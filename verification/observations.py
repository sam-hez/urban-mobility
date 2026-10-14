import os

import pandas as pd

from common import DISTANCE_BINS, LOG_DIR, PROCESSED_DIR, add_counts, cut, iter_clean
from algorithms import top_k_routes

AIRPORT_ZONES = {1, 132, 138}


def add_sums(target, groups, value_columns):
    for key, group in groups:
        key = str(key)
        entry = target.setdefault(key, {"trips": 0, **{c: 0.0 for c in value_columns}})
        entry["trips"] += len(group)
        for column in value_columns:
            entry[column] += float(group[column].sum())


def frame_from(target, key_name):
    rows = []
    for key, entry in target.items():
        rows.append({key_name: key, **entry})
    return pd.DataFrame(rows)


def main():
    by_hour = {}
    by_weekend = {}
    by_borough = {}
    by_distance = {}
    by_period_tip = {}
    daily = {}
    weekend_days = {}
    airport = {"trips": 0, "fare": 0.0, "distance": 0.0}
    overall = {"trips": 0, "fare": 0.0, "distance": 0.0}
    kept_pairs = []

    columns = [
        "pickup_date", "pickup_hour", "is_weekend", "pickup_borough", "trip_distance", "fare_amount",
        "avg_speed_mph", "fare_per_mile", "tip_pct", "time_period", "pickup_location_id", "dropoff_location_id",
    ]
    for df in iter_clean(columns=columns):
        add_sums(by_hour, df.groupby("pickup_hour"), ["avg_speed_mph", "fare_amount"])
        add_sums(by_weekend, df.groupby("is_weekend"), ["avg_speed_mph", "fare_amount"])
        add_sums(by_borough, df.groupby("pickup_borough"), ["fare_amount"])
        df["distance_bin"] = cut(df["trip_distance"], DISTANCE_BINS)
        add_sums(by_distance, df.groupby("distance_bin"), ["fare_amount", "trip_distance"])
        card = df[df["tip_pct"].notna()]
        add_sums(by_period_tip, card.groupby("time_period"), ["tip_pct"])
        add_counts(daily, df["pickup_date"])
        for flag, group in df.groupby("is_weekend"):
            weekend_days.setdefault(int(flag), set()).update(group["pickup_date"].unique().tolist())
        near_airport = df["pickup_location_id"].isin(AIRPORT_ZONES) | df["dropoff_location_id"].isin(AIRPORT_ZONES)
        airport["trips"] += int(near_airport.sum())
        airport["fare"] += float(df.loc[near_airport, "fare_amount"].sum())
        airport["distance"] += float(df.loc[near_airport, "trip_distance"].sum())
        overall["trips"] += len(df)
        overall["fare"] += float(df["fare_amount"].sum())
        overall["distance"] += float(df["trip_distance"].sum())
        kept_pairs.append(df[["pickup_location_id", "dropoff_location_id"]])

    lines = []

    hours = frame_from(by_hour, "hour")
    hours["hour"] = hours["hour"].astype(int)
    hours = hours.sort_values("hour")
    hours["avg_speed_mph"] = (hours["avg_speed_mph"] / hours["trips"]).round(2)
    hours["avg_fare"] = (hours["fare_amount"] / hours["trips"]).round(2)
    hours = hours[["hour", "trips", "avg_speed_mph", "avg_fare"]]
    lines.append("Trips, average speed and average fare by pickup hour")
    lines.append(hours.to_string(index=False))
    lines.append("")

    weekend = frame_from(by_weekend, "is_weekend")
    weekend["days"] = weekend["is_weekend"].map(lambda f: len(weekend_days.get(int(f), [])))
    weekend["trips_per_day"] = (weekend["trips"] / weekend["days"]).round(0)
    weekend["avg_speed_mph"] = (weekend["avg_speed_mph"] / weekend["trips"]).round(2)
    weekend["avg_fare"] = (weekend["fare_amount"] / weekend["trips"]).round(2)
    weekend["day_type"] = weekend["is_weekend"].map(lambda f: "weekend" if int(f) == 1 else "weekday")
    lines.append("Weekday and weekend")
    lines.append(weekend[["day_type", "days", "trips", "trips_per_day", "avg_speed_mph", "avg_fare"]].to_string(index=False))
    lines.append("")

    boroughs = frame_from(by_borough, "pickup_borough")
    boroughs["share_pct"] = (boroughs["trips"] / boroughs["trips"].sum() * 100).round(2)
    boroughs["avg_fare"] = (boroughs["fare_amount"] / boroughs["trips"]).round(2)
    boroughs = boroughs.sort_values("trips", ascending=False)
    lines.append("Pickups by borough")
    lines.append(boroughs[["pickup_borough", "trips", "share_pct", "avg_fare"]].to_string(index=False))
    lines.append("")

    distances = frame_from(by_distance, "distance_bin")
    distances["avg_fare"] = (distances["fare_amount"] / distances["trips"]).round(2)
    distances["fare_per_mile"] = (distances["fare_amount"] / distances["trip_distance"]).round(2)
    distances["order"] = distances["distance_bin"].map({label: i for i, label in enumerate(DISTANCE_BINS[1])})
    distances = distances.sort_values("order")
    lines.append("Fare by trip distance")
    lines.append(distances[["distance_bin", "trips", "avg_fare", "fare_per_mile"]].to_string(index=False))
    lines.append("")

    tips = frame_from(by_period_tip, "time_period")
    tips["avg_tip_pct"] = (tips["tip_pct"] / tips["trips"]).round(2)
    lines.append("Average tip percent on card trips by time of day")
    lines.append(tips[["time_period", "trips", "avg_tip_pct"]].to_string(index=False))
    lines.append("")

    def pairs():
        for frame in kept_pairs:
            for pickup, dropoff in zip(frame["pickup_location_id"].tolist(), frame["dropoff_location_id"].tolist()):
                yield pickup, dropoff

    zones = pd.read_csv(os.path.join(PROCESSED_DIR, "zones.csv"), keep_default_na=False)
    names = {int(r.location_id): r.zone for r in zones.itertuples()}
    routes = [{"pickup_zone": names[a], "dropoff_zone": names[b], "trips": c} for c, (a, b) in top_k_routes(pairs(), 10)]
    lines.append("Top 10 routes")
    lines.append(pd.DataFrame(routes).to_string(index=False))
    lines.append("")

    airport_share = airport["trips"] / overall["trips"] * 100
    airport_fare = airport["fare"] / airport["trips"] if airport["trips"] else 0
    overall_fare = overall["fare"] / overall["trips"]
    lines.append("Airport trips (Newark, JFK, LaGuardia as pickup or dropoff)")
    lines.append("  trips {} ({:.2f}% of all), average fare {:.2f}, average fare overall {:.2f}".format(
        airport["trips"], airport_share, airport_fare, overall_fare))
    lines.append("")

    busiest = hours.loc[hours["trips"].idxmax()]
    slowest = hours.loc[hours["avg_speed_mph"].idxmin()]
    fastest = hours.loc[hours["avg_speed_mph"].idxmax()]
    top_day = max(daily.items(), key=lambda item: item[1])
    low_day = min(daily.items(), key=lambda item: item[1])
    top_borough = boroughs.iloc[0]
    short = distances.iloc[0]
    long = distances.iloc[-1]

    lines.append("Candidate observations (check each against the dashboard before using it)")
    lines.append("1. The busiest hour is {}:00 with {} trips, and the slowest traffic is at {}:00 ({} mph) against {} mph at {}:00.".format(
        int(busiest["hour"]), int(busiest["trips"]), int(slowest["hour"]), slowest["avg_speed_mph"], fastest["avg_speed_mph"], int(fastest["hour"])))
    lines.append("2. {} generates {:.1f}% of all pickups, and the busiest day is {} with {} trips against {} on {}.".format(
        top_borough["pickup_borough"], top_borough["share_pct"], top_day[0], top_day[1], low_day[1], low_day[0]))
    lines.append("3. Fare per mile falls from {} for trips of {} to {} for trips of {}, so short trips cost far more per mile.".format(
        short["fare_per_mile"], short["distance_bin"], long["fare_per_mile"], long["distance_bin"]))
    lines.append("4. Airport trips are {:.1f}% of all trips but average a fare of {:.2f} against {:.2f} overall.".format(
        airport_share, airport_fare, overall_fare))
    lines.append("")

    text = "\n".join(lines)
    print(text)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "observations.txt"), "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


if __name__ == "__main__":
    main()
