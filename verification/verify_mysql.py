import argparse
import csv
import getpass
import os

import pandas as pd
import pymysql

from common import (
    DISTANCE_BINS, FARE_BINS, LOG_DIR, PROCESSED_DIR, SPEED_BINS,
    add_bins, add_counts, case_sql, iter_clean,
)
from algorithms import top_k_routes

NUMERIC_COLUMNS = [
    "trip_distance", "fare_amount", "tip_amount", "tolls_amount", "total_amount",
    "duration_min", "passenger_count", "avg_speed_mph", "fare_per_mile", "tip_pct",
]

GROUP_COLUMNS = {
    "pickup_date": "pickup_date",
    "pickup_hour": "pickup_hour",
    "pickup_weekday": "pickup_dow",
    "payment_type": "payment_type_id",
    "vendor": "vendor_id",
    "rate_code": "rate_code_id",
    "time_period": "time_period",
    "pickup_zone": "pickup_location_id",
    "dropoff_zone": "dropoff_location_id",
}

BIN_GROUPS = {
    "distance_bin": ("trip_distance", DISTANCE_BINS),
    "fare_bin": ("fare_amount", FARE_BINS),
    "speed_bin": ("avg_speed_mph", SPEED_BINS),
}

INVALID_CHECKS = [
    ("distance not positive or above 100", "{trip_distance} <= 0 OR {trip_distance} > 100"),
    ("fare not between 0 and 500", "{fare_amount} <= 0 OR {fare_amount} > 500"),
    ("total not between 0 and 1000", "{total_amount} <= 0 OR {total_amount} > 1000"),
    ("negative tip or tolls", "{tip_amount} < 0 OR {tolls_amount} < 0"),
    ("tip above 500", "{tip_amount} > 500"),
    ("total below fare", "{total_amount} < {fare_amount}"),
    ("duration outside 1 to 180 minutes", "{duration_min} < 1 OR {duration_min} > 180"),
    ("dropoff not after pickup", "{dropoff_datetime} <= {pickup_datetime}"),
    ("passenger count outside 1 to 6", "{passenger_count} < 1 OR {passenger_count} > 6"),
    ("speed above 80 mph", "{trip_distance} / ({duration_min} / 60) > 80"),
]

ENGINEERED_CHECKS = [
    ("duration_min matches the two times", "ABS(TIMESTAMPDIFF(SECOND, {pickup_datetime}, {dropoff_datetime}) / 60 - {duration_min}) > 0.02"),
    ("avg_speed_mph matches distance and duration", "ABS({avg_speed_mph} - {trip_distance} / ({duration_min} / 60)) > 0.05"),
    ("fare_per_mile matches fare and distance", "ABS({fare_per_mile} - {fare_amount} / {trip_distance}) > 0.02"),
    ("tip_pct matches tip and fare on card trips", "{payment_type_id} = 1 AND ABS({tip_pct} - {tip_amount} / {fare_amount} * 100) > 0.02"),
    ("tip_pct set on a non-card trip", "{payment_type_id} <> 1 AND {tip_pct} IS NOT NULL"),
    ("tip_pct empty on a card trip", "{payment_type_id} = 1 AND {tip_pct} IS NULL"),
    ("pickup_date matches pickup time", "{pickup_date} <> DATE({pickup_datetime})"),
    ("pickup_hour matches pickup time", "{pickup_hour} <> HOUR({pickup_datetime})"),
    ("pickup_dow matches pickup time", "{pickup_dow} <> WEEKDAY({pickup_datetime})"),
    ("is_weekend matches weekday", "{is_weekend} <> (WEEKDAY({pickup_datetime}) >= 5)"),
    ("time_period matches pickup hour", "{time_period} <> CASE WHEN HOUR({pickup_datetime}) <= 5 THEN 'night' WHEN HOUR({pickup_datetime}) <= 10 THEN 'morning' WHEN HOUR({pickup_datetime}) <= 15 THEN 'midday' WHEN HOUR({pickup_datetime}) <= 20 THEN 'evening' ELSE 'late_night' END"),
]


class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, section, name, expected, actual):
        self.rows.append((status, section, name, str(expected), str(actual)))
        print("[{}] {} | {} | expected {} | actual {}".format(status, section, name, expected, actual))

    def equal(self, section, name, expected, actual):
        self.add("PASS" if expected == actual else "FAIL", section, name, expected, actual)

    def close(self, section, name, expected, actual):
        ok = abs(expected - actual) <= max(0.01, abs(expected) * 1e-6)
        self.add("PASS" if ok else "FAIL", section, name, round(expected, 4), round(actual, 4))

    def zero(self, section, name, actual):
        self.add("PASS" if actual == 0 else "FAIL", section, name, 0, actual)

    def counts(self, section, name, expected, actual):
        keys = set(expected) | set(actual)
        different = [k for k in sorted(keys) if expected.get(k, 0) != actual.get(k, 0)]
        if not different:
            self.add("PASS", section, name, "{} groups".format(len(expected)), "all groups match")
        else:
            key = different[0]
            detail = "{} groups differ, first {}: expected {} actual {}".format(
                len(different), key, expected.get(key, 0), actual.get(key, 0))
            self.add("FAIL", section, name, "{} groups".format(len(expected)), detail)

    def skip(self, section, name, reason):
        self.add("SKIP", section, name, "-", reason)

    def warn(self, section, name, detail):
        self.add("WARN", section, name, "-", detail)

    def info(self, section, name, detail):
        self.add("INFO", section, name, "-", detail)

    def save(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "database_verification.csv"), "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["status", "section", "check", "expected", "actual"])
            writer.writerows(self.rows)
        with open(os.path.join(LOG_DIR, "database_verification.txt"), "w", encoding="utf-8") as handle:
            for status, section, name, expected, actual in self.rows:
                handle.write("[{}] {} | {} | expected {} | actual {}\n".format(status, section, name, expected, actual))

    def totals(self):
        result = {}
        for row in self.rows:
            result[row[0]] = result.get(row[0], 0) + 1
        return result


class Database:
    def __init__(self, args, column_map):
        self.connection = pymysql.connect(
            host=args.host, port=args.port, user=args.user, password=args.password,
            database=args.database, charset="utf8mb4",
        )
        self.trips = "`{}`".format(args.trips_table)
        self.zones = "`{}`".format(args.zones_table)
        self.zone_id = "`{}`".format(args.zone_id_column)
        self.zone_name = "`{}`".format(args.zone_name_column) if args.zone_name_column else None
        self.column_map = column_map
        cursor = self.connection.cursor()
        cursor.execute("SHOW COLUMNS FROM " + self.trips)
        self.existing = set(row[0] for row in cursor.fetchall())
        cursor.close()

    def actual(self, standard):
        return self.column_map.get(standard, standard)

    def has(self, *standards):
        return all(self.actual(s) in self.existing for s in standards)

    def quoted(self):
        return {s: "`{}`".format(self.actual(s)) for s in self.column_map_all()}

    def column_map_all(self):
        names = set(self.column_map) | set(NUMERIC_COLUMNS) | set(GROUP_COLUMNS.values())
        names |= {
            "pickup_datetime", "dropoff_datetime", "pickup_location_id", "dropoff_location_id",
            "pickup_date", "pickup_hour", "pickup_dow", "is_weekend", "time_period", "tip_pct",
        }
        return names

    def query(self, sql):
        cursor = self.connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def scalar(self, sql):
        return self.query(sql)[0][0]

    def row(self, sql):
        return self.query(sql)[0]


def profile_parquet(batch_size):
    profile = {
        "rows": 0, "sums": {}, "mins": {}, "maxs": {}, "nulls": {},
        "groups": {name: {} for name in list(GROUP_COLUMNS) + list(BIN_GROUPS)},
    }
    for df in iter_clean(batch_size=batch_size):
        profile["rows"] += len(df)
        for column in NUMERIC_COLUMNS:
            values = df[column]
            profile["sums"][column] = profile["sums"].get(column, 0.0) + float(values.sum())
            if values.notna().any():
                low = float(values.min())
                high = float(values.max())
                profile["mins"][column] = min(profile["mins"].get(column, low), low)
                profile["maxs"][column] = max(profile["maxs"].get(column, high), high)
        for column in df.columns:
            profile["nulls"][column] = profile["nulls"].get(column, 0) + int(df[column].isna().sum())
        df = add_bins(df)
        for name, column in GROUP_COLUMNS.items():
            add_counts(profile["groups"][name], df[column])
        for name in BIN_GROUPS:
            add_counts(profile["groups"][name], df[name])
    return profile


def main_month(profile):
    months = {}
    for day, count in profile["groups"]["pickup_date"].items():
        months[day[:7]] = months.get(day[:7], 0) + count
    return max(months, key=months.get)


def check_row_counts(db, report, profile, zones_csv, args):
    section = "Row counts"
    report.equal(section, "trips table", profile["rows"], db.scalar("SELECT COUNT(*) FROM " + db.trips))
    report.equal(section, "zones table", len(zones_csv), db.scalar("SELECT COUNT(*) FROM " + db.zones))
    if db.has("pickup_date") or db.has("pickup_datetime"):
        expression = "`{}`".format(db.actual("pickup_date")) if db.has("pickup_date") else "DATE(`{}`)".format(db.actual("pickup_datetime"))
        actual = {str(k): int(c) for k, c in db.query("SELECT {} AS k, COUNT(*) FROM {} GROUP BY k".format(expression, db.trips))}
        report.counts(section, "trips per day", profile["groups"]["pickup_date"], actual)


def check_invalid(db, report, profile):
    section = "Invalid data"
    quoted = db.quoted()
    month = main_month(profile)
    start = pd.Period(month, "M").start_time.strftime("%Y-%m-%d")
    end = (pd.Period(month, "M") + 1).start_time.strftime("%Y-%m-%d")
    checks = list(INVALID_CHECKS)
    checks.append(("pickup outside {}".format(month), "NOT ({pickup_datetime} >= '" + start + "' AND {pickup_datetime} < '" + end + "')"))
    runnable = []
    for name, template in checks:
        needed = [k for k in db.column_map_all() if "{" + k + "}" in template]
        if db.has(*needed):
            runnable.append((name, template.format(**quoted)))
        else:
            report.skip(section, name, "needed column is not in the trips table")
    if not runnable:
        return
    sql = "SELECT " + ", ".join("COALESCE(SUM(({})), 0)".format(cond) for _, cond in runnable) + " FROM " + db.trips
    for (name, _), value in zip(runnable, db.row(sql)):
        report.zero(section, name, int(value))


def check_duplicates(db, report):
    section = "Invalid data"
    needed = ["pickup_datetime", "dropoff_datetime", "pickup_location_id", "dropoff_location_id", "trip_distance", "fare_amount", "total_amount"]
    if not db.has(*needed):
        report.skip(section, "duplicate trips", "needed column is not in the trips table")
        return
    columns = ", ".join("`{}`".format(db.actual(n)) for n in needed)
    sql = "SELECT COUNT(*) FROM (SELECT 1 FROM {} GROUP BY {} HAVING COUNT(*) > 1) d".format(db.trips, columns)
    report.zero(section, "duplicate trips", int(db.scalar(sql)))


def check_zones(db, report, profile, zones_csv):
    section = "Zone mapping"
    table_rows = db.query("SELECT {}{} FROM {}".format(db.zone_id, ", " + db.zone_name if db.zone_name else "", db.zones))
    table_ids = set(int(r[0]) for r in table_rows)
    csv_ids = set(int(i) for i in zones_csv["location_id"])
    report.equal(section, "zone ids match zones.csv", "0 missing, 0 extra", "{} missing, {} extra".format(len(csv_ids - table_ids), len(table_ids - csv_ids)))
    if db.zone_name:
        names = {int(r[0]): str(r[1]).strip() for r in table_rows}
        expected = {int(r.location_id): str(r.zone).strip() for r in zones_csv.itertuples()}
        different = [i for i in expected if i in names and names[i] != expected[i]]
        report.zero(section, "zone names differ from zones.csv", len(different))
    for column, label in [("pickup_location_id", "pickup"), ("dropoff_location_id", "dropoff")]:
        if not db.has(column):
            report.skip(section, label + " zones without a match", "column not in the trips table")
            continue
        sql = "SELECT COUNT(*) FROM {t} x LEFT JOIN {z} z ON z.{i} = x.`{c}` WHERE z.{i} IS NULL".format(
            t=db.trips, z=db.zones, i=db.zone_id, c=db.actual(column))
        report.zero(section, label + " zone ids with no match in zones table", int(db.scalar(sql)))
    for group, column in [("pickup_zone", "pickup_location_id"), ("dropoff_zone", "dropoff_location_id")]:
        if db.has(column):
            actual = {str(k): int(c) for k, c in db.query("SELECT `{c}`, COUNT(*) FROM {t} GROUP BY `{c}`".format(c=db.actual(column), t=db.trips))}
            report.counts(section, "trips per " + group.replace("_", " "), profile["groups"][group], actual)


def check_nulls(db, report, profile):
    section = "Nulls"
    columns = [c for c in profile["nulls"] if db.has(c)]
    missing = [c for c in profile["nulls"] if not db.has(c)]
    if missing:
        report.info(section, "columns of the cleaned file not in the trips table", ", ".join(missing))
    if not columns:
        return
    sql = "SELECT " + ", ".join("COALESCE(SUM(`{}` IS NULL), 0)".format(db.actual(c)) for c in columns) + " FROM " + db.trips
    for column, value in zip(columns, db.row(sql)):
        report.equal(section, "null count in " + column, profile["nulls"][column], int(value))


def check_engineered(db, report):
    section = "Engineered fields"
    quoted = db.quoted()
    runnable = []
    for name, template in ENGINEERED_CHECKS:
        needed = [k for k in db.column_map_all() if "{" + k + "}" in template]
        if db.has(*needed):
            runnable.append((name, template.format(**quoted)))
        else:
            report.skip(section, name, "needed column is not in the trips table")
    if not runnable:
        return
    sql = "SELECT " + ", ".join("COALESCE(SUM(({})), 0)".format(cond) for _, cond in runnable) + " FROM " + db.trips
    for (name, _), value in zip(runnable, db.row(sql)):
        report.zero(section, "rows where " + name + " is wrong", int(value))


def check_distributions(db, report, profile):
    section = "Distributions"
    columns = [c for c in NUMERIC_COLUMNS if db.has(c)]
    if columns:
        parts = []
        for c in columns:
            q = "`{}`".format(db.actual(c))
            parts.append("COALESCE(SUM({q}), 0), MIN({q}), MAX({q})".format(q=q))
        values = db.row("SELECT " + ", ".join(parts) + " FROM " + db.trips)
        for i, c in enumerate(columns):
            total, low, high = values[i * 3], values[i * 3 + 1], values[i * 3 + 2]
            report.close(section, "sum of " + c, profile["sums"][c], float(total))
            if c in profile["mins"] and low is not None:
                report.close(section, "min of " + c, profile["mins"][c], float(low))
                report.close(section, "max of " + c, profile["maxs"][c], float(high))
    expressions = {}
    for name, column in GROUP_COLUMNS.items():
        if name in ("pickup_date", "pickup_zone", "dropoff_zone"):
            continue
        if db.has(column):
            expressions[name] = "`{}`".format(db.actual(column))
        elif column == "pickup_hour" and db.has("pickup_datetime"):
            expressions[name] = "HOUR(`{}`)".format(db.actual("pickup_datetime"))
        elif column == "pickup_dow" and db.has("pickup_datetime"):
            expressions[name] = "WEEKDAY(`{}`)".format(db.actual("pickup_datetime"))
    for name, (column, bins) in BIN_GROUPS.items():
        if db.has(column):
            expressions[name] = case_sql("`{}`".format(db.actual(column)), bins)
    for name, expression in expressions.items():
        actual = {str(k): int(c) for k, c in db.query("SELECT {} AS k, COUNT(*) FROM {} GROUP BY k".format(expression, db.trips))}
        report.counts(section, "trips by " + name.replace("_", " "), profile["groups"][name], actual)

    daily = profile["groups"]["pickup_date"]
    median = sorted(daily.values())[len(daily) // 2]
    for day, count in sorted(daily.items()):
        if count < median * 0.5:
            report.warn(section, "unusually quiet day " + day, "{} trips, median day has {}".format(count, median))
    hours = profile["groups"]["pickup_hour"]
    for hour in range(24):
        if str(hour) not in hours:
            report.warn(section, "no trips at hour {}".format(hour), "check the pickup times")
    zone_total = profile["rows"]
    busiest = max(profile["groups"]["pickup_zone"].items(), key=lambda item: item[1])
    if busiest[1] / zone_total > 0.2:
        report.warn(section, "one pickup zone has over 20% of trips", "zone {} has {:.1f}%".format(busiest[0], busiest[1] / zone_total * 100))


def check_algorithm(db, report, k=10):
    section = "Algorithm"
    if not db.has("pickup_location_id", "dropoff_location_id"):
        report.skip(section, "top routes", "zone id columns are not in the trips table")
        return

    def pairs():
        for df in iter_clean(columns=["pickup_location_id", "dropoff_location_id"]):
            for pickup, dropoff in zip(df["pickup_location_id"].tolist(), df["dropoff_location_id"].tolist()):
                yield pickup, dropoff

    mine = top_k_routes(pairs(), k)

    counts = {}
    for df in iter_clean(columns=["pickup_location_id", "dropoff_location_id"]):
        for key, count in df.groupby(["pickup_location_id", "dropoff_location_id"]).size().items():
            counts[key] = counts.get(key, 0) + int(count)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    baseline = [(count, (int(key[0]), int(key[1]))) for key, count in ordered[:k]]
    report.equal(section, "own heap top {} routes equal the pandas baseline".format(k), baseline, mine)

    pu = "`{}`".format(db.actual("pickup_location_id"))
    do = "`{}`".format(db.actual("dropoff_location_id"))
    sql = "SELECT {pu}, {do}, COUNT(*) c FROM {t} GROUP BY {pu}, {do} ORDER BY c DESC, {pu} ASC, {do} ASC LIMIT {k}".format(pu=pu, do=do, t=db.trips, k=k)
    from_mysql = [(int(c), (int(a), int(b))) for a, b, c in db.query(sql)]
    report.equal(section, "own heap top {} routes equal the MySQL GROUP BY".format(k), from_mysql, mine)
    report.info(section, "busiest route", "{} trips from zone {} to zone {}".format(mine[0][0], mine[0][1][0], mine[0][1][1]) if mine else "no trips")


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD"))
    parser.add_argument("--database", default="urban_mobility")
    parser.add_argument("--trips-table", default="trips")
    parser.add_argument("--zones-table", default="zones")
    parser.add_argument("--zone-id-column", default="location_id")
    parser.add_argument("--zone-name-column", default=None)
    parser.add_argument("--map", action="append", default=[], help="standard_name=actual_column, for example pickup_location_id=PULocationID")
    parser.add_argument("--batch-size", type=int, default=500000)
    parser.add_argument("--check-duplicates", action="store_true", help="slow on millions of rows")
    parser.add_argument("--skip-algorithm", action="store_true")
    args = parser.parse_args()
    if args.password is None:
        args.password = getpass.getpass("MySQL password for {} (press Enter if none): ".format(args.user))
    return args


def main():
    args = parse_arguments()
    column_map = {}
    for item in args.map:
        standard, actual = item.split("=", 1)
        column_map[standard.strip()] = actual.strip()

    zones_csv = pd.read_csv(os.path.join(PROCESSED_DIR, "zones.csv"), keep_default_na=False)
    db = Database(args, column_map)
    report = Report()

    print("Reading the cleaned parquet file")
    profile = profile_parquet(args.batch_size)
    print("Cleaned file has {} rows".format(profile["rows"]))
    print("Columns in the MySQL trips table: {}".format(len(db.existing)))
    print()

    check_row_counts(db, report, profile, zones_csv, args)
    check_invalid(db, report, profile)
    if args.check_duplicates:
        check_duplicates(db, report)
    check_zones(db, report, profile, zones_csv)
    check_nulls(db, report, profile)
    check_engineered(db, report)
    check_distributions(db, report, profile)
    if not args.skip_algorithm:
        check_algorithm(db, report)

    report.save()
    totals = report.totals()
    print()
    print("Summary:", ", ".join("{} {}".format(k, v) for k, v in sorted(totals.items())))
    print("Saved logs/database_verification.txt and logs/database_verification.csv")
    if totals.get("FAIL", 0) > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
