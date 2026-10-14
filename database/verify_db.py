import os
import sys

import pyarrow.parquet as pq
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from load_db import TRIPS_FILE, get_engine

EXPECTED_TABLES = {"boroughs", "service_zones", "zones", "vendors",
                   "rate_codes", "payment_types", "trips"}

EXPECTED_FOREIGN_KEYS = {
    ("zones", "borough_id", "boroughs", "borough_id"),
    ("zones", "service_zone_id", "service_zones", "service_zone_id"),
    ("trips", "vendor_id", "vendors", "vendor_id"),
    ("trips", "pickup_location_id", "zones", "location_id"),
    ("trips", "dropoff_location_id", "zones", "location_id"),
    ("trips", "rate_code_id", "rate_codes", "rate_code_id"),
    ("trips", "payment_type_id", "payment_types", "payment_type_id"),
}

EXPECTED_INDEXES = {"idx_trips_pickup_dt", "idx_trips_pu_dt", "idx_trips_distance", "idx_trips_total"}

EXPECTED_CHECKS = {"chk_times", "chk_distance", "chk_fare", "chk_total",
                   "chk_tip_tolls", "chk_passengers", "chk_duration", "chk_flag"}

GOOD_TRIP = {
    "vendor_id": 1, "pickup_datetime": "2019-01-15 10:00:00", "dropoff_datetime": "2019-01-15 10:20:00",
    "pickup_location_id": 161, "dropoff_location_id": 237, "rate_code_id": 1, "payment_type_id": 1,
    "passenger_count": 1, "trip_distance": 2.5, "store_and_fwd_flag": "N",
    "fare_amount": 12.0, "extra": 0.5, "mta_tax": 0.5, "tip_amount": 2.0, "tolls_amount": 0.0,
    "improvement_surcharge": 0.3, "congestion_surcharge": 0.0, "airport_fee": 0.0,
    "total_amount": 15.3, "duration_min": 20.0,
}

BAD_TRIPS = [
    ("dropoff before pickup",          {"dropoff_datetime": "2019-01-15 09:00:00"}),
    ("distance is 0",                  {"trip_distance": 0}),
    ("distance above 100 miles",       {"trip_distance": 150}),
    ("fare is 0",                      {"fare_amount": 0}),
    ("fare above 500",                 {"fare_amount": 600, "total_amount": 650}),
    ("total below the fare",           {"total_amount": 5}),
    ("total above 1000",               {"total_amount": 1500}),
    ("negative tip",                   {"tip_amount": -1}),
    ("tip above 500",                  {"tip_amount": 600}),
    ("negative tolls",                 {"tolls_amount": -2}),
    ("0 passengers",                   {"passenger_count": 0}),
    ("7 passengers",                   {"passenger_count": 7}),
    ("duration under 1 minute",        {"duration_min": 0.5}),
    ("duration over 180 minutes",      {"duration_min": 181}),
    ("store_and_fwd_flag is 'X'",      {"store_and_fwd_flag": "X"}),
    ("unknown pickup zone",            {"pickup_location_id": 999}),
    ("unknown dropoff zone",           {"dropoff_location_id": 999}),
    ("unknown vendor",                 {"vendor_id": 99}),
    ("unknown rate code",              {"rate_code_id": 50}),
    ("unknown payment type",           {"payment_type_id": 50}),
    ("missing pickup time (NULL)",     {"pickup_datetime": None}),
    ("missing distance (NULL)",        {"trip_distance": None}),
]

passed = 0
failed = 0


def check(ok, message):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {message}")
    else:
        failed += 1
        print(f"  FAIL  {message}")


def column_of(conn, sql):
    return {row[0] for row in conn.execute(text(sql)).fetchall()}


def insert_is_accepted(engine, table, values):
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"), values)
            return True
        except DBAPIError:
            return False
        finally:
            transaction.rollback()


def verify_structure(engine):
    print("\n1. Tables, keys and indexes")
    with engine.connect() as conn:
        tables = column_of(conn, "SELECT table_name FROM information_schema.tables "
                                 "WHERE table_schema = DATABASE()")
        check(tables == EXPECTED_TABLES, f"7 tables exist ({', '.join(sorted(EXPECTED_TABLES - tables)) or 'none missing'})")

        with_pk = column_of(conn, "SELECT table_name FROM information_schema.table_constraints "
                                  "WHERE table_schema = DATABASE() AND constraint_type = 'PRIMARY KEY'")
        check(with_pk == EXPECTED_TABLES, "every table has a primary key")

        foreign_keys = {tuple(row) for row in conn.execute(text(
            "SELECT table_name, column_name, referenced_table_name, referenced_column_name "
            "FROM information_schema.key_column_usage "
            "WHERE table_schema = DATABASE() AND referenced_table_name IS NOT NULL")).fetchall()}
        check(foreign_keys == EXPECTED_FOREIGN_KEYS, f"7 foreign keys exist ({len(foreign_keys)} found)")

        indexes = column_of(conn, "SELECT index_name FROM information_schema.statistics "
                                  "WHERE table_schema = DATABASE() AND table_name = 'trips'")
        check(EXPECTED_INDEXES <= indexes, f"the 4 trips indexes exist ({', '.join(sorted(EXPECTED_INDEXES - indexes)) or 'none missing'})")

        checks = column_of(conn, "SELECT constraint_name FROM information_schema.check_constraints "
                                 "WHERE constraint_schema = DATABASE()")
        check(EXPECTED_CHECKS <= checks, f"the 8 CHECK constraints exist ({', '.join(sorted(EXPECTED_CHECKS - checks)) or 'none missing'})")


def verify_constraints(engine):
    print("\n2. Constraints refuse bad rows (every test insert is rolled back)")
    check(insert_is_accepted(engine, "trips", GOOD_TRIP),
          "control: a correct trip IS accepted (so the tests below are fair)")
    for description, change in BAD_TRIPS:
        check(not insert_is_accepted(engine, "trips", {**GOOD_TRIP, **change}),
              f"refused: {description}")
    check(not insert_is_accepted(engine, "zones", {"location_id": 1, "zone_name": "Copy", "borough_id": 1, "service_zone_id": 1}),
          "refused: a second zone with an existing id (primary key)")
    check(not insert_is_accepted(engine, "boroughs", {"borough_name": "Manhattan"}),
          "refused: a second borough with an existing name (unique)")


def verify_data(engine):
    print("\n3. Loaded data")
    with engine.connect() as conn:
        counts = {t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in sorted(EXPECTED_TABLES)}
        check(counts["trips"] > 0 and counts["zones"] == 265, f"trips: {counts['trips']:,}, zones: {counts['zones']}")

        if os.path.exists(TRIPS_FILE):
            in_file = pq.ParquetFile(TRIPS_FILE).metadata.num_rows
            if counts["trips"] == in_file:
                check(True, f"all {in_file:,} trips of the cleaned file are in the database")
            else:
                print(f"  INFO  partial load: {counts['trips']:,} of {in_file:,} trips (fine for a test load with --limit)")

        first, last = conn.execute(text("SELECT MIN(pickup_datetime), MAX(pickup_datetime) FROM trips")).fetchone()
        print(f"  INFO  pickups run from {first} to {last}")

        orphans = conn.execute(text("""
            SELECT COALESCE(SUM(pz.location_id IS NULL), 0), COALESCE(SUM(dz.location_id IS NULL), 0),
                   COALESCE(SUM(v.vendor_id IS NULL), 0), COALESCE(SUM(r.rate_code_id IS NULL), 0),
                   COALESCE(SUM(p.payment_type_id IS NULL), 0)
            FROM trips t
            LEFT JOIN zones pz         ON pz.location_id = t.pickup_location_id
            LEFT JOIN zones dz         ON dz.location_id = t.dropoff_location_id
            LEFT JOIN vendors v        ON v.vendor_id = t.vendor_id
            LEFT JOIN rate_codes r     ON r.rate_code_id = t.rate_code_id
            LEFT JOIN payment_types p  ON p.payment_type_id = t.payment_type_id
        """)).fetchone()
        check(sum(orphans) == 0, "every trip joins to its zones, vendor, rate code and payment type")

        broken = conn.execute(text("""
            SELECT COALESCE(SUM(dropoff_datetime <= pickup_datetime), 0),
                   COALESCE(SUM(trip_distance <= 0 OR trip_distance > 100), 0),
                   COALESCE(SUM(fare_amount <= 0 OR fare_amount > 500), 0),
                   COALESCE(SUM(total_amount <= 0 OR total_amount > 1000 OR total_amount < fare_amount), 0),
                   COALESCE(SUM(tip_amount < 0 OR tip_amount > 500 OR tolls_amount < 0), 0),
                   COALESCE(SUM(passenger_count < 1 OR passenger_count > 6), 0),
                   COALESCE(SUM(duration_min < 1 OR duration_min > 180), 0),
                   COALESCE(SUM(store_and_fwd_flag IS NOT NULL AND store_and_fwd_flag NOT IN ('Y', 'N')), 0)
            FROM trips
        """)).fetchone()
        check(sum(broken) == 0, f"no loaded trip breaks a rule (counts per rule: {[int(n) for n in broken]})")


def verify_index_use(engine):
    print("\n4. Indexes are used by the common queries (EXPLAIN)")
    with engine.connect() as conn:
        day = conn.execute(text("SELECT DATE(MIN(pickup_datetime)) FROM trips")).scalar()
        queries = [
            ("one zone on one day",       "SELECT trip_id FROM trips WHERE pickup_location_id = 161 "
                                          "AND pickup_datetime >= :day AND pickup_datetime < DATE_ADD(:day, INTERVAL 1 DAY)"),
            ("newest trips (time sort)",  "SELECT trip_id FROM trips ORDER BY pickup_datetime DESC, trip_id DESC LIMIT 25"),
            ("longest trips (distance)",  "SELECT trip_id FROM trips WHERE trip_distance > 20 ORDER BY trip_distance DESC LIMIT 20"),
            ("most expensive (fare)",     "SELECT trip_id FROM trips WHERE total_amount BETWEEN 100 AND 300 ORDER BY total_amount DESC LIMIT 20"),
        ]
        for name, sql in queries:
            plan = conn.execute(text("EXPLAIN " + sql), {"day": str(day)}).mappings().fetchone()
            check(plan["key"] is not None, f"{name}: uses index {plan['key']}")


def main():
    engine = get_engine()
    print("Checking the database...")
    verify_structure(engine)
    verify_constraints(engine)
    verify_data(engine)
    verify_index_use(engine)
    print(f"\n{passed} checks passed, {failed} failed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()