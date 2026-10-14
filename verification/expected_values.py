import argparse
import json
import os

import pandas as pd

from common import DISTANCE_BINS, PROCESSED_DIR, add_counts, cut, iter_clean
from algorithms import top_k_routes


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--borough")
    parser.add_argument("--hour-from", type=int)
    parser.add_argument("--hour-to", type=int)
    parser.add_argument("--min-distance", type=float)
    parser.add_argument("--max-distance", type=float)
    parser.add_argument("--min-fare", type=float)
    parser.add_argument("--max-fare", type=float)
    parser.add_argument("--payment-type", type=int)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def apply_filters(df, args):
    mask = pd.Series(True, index=df.index)
    if args.start_date:
        mask &= df["pickup_date"] >= args.start_date
    if args.end_date:
        mask &= df["pickup_date"] <= args.end_date
    if args.borough:
        mask &= df["pickup_borough"] == args.borough
    if args.hour_from is not None:
        mask &= df["pickup_hour"] >= args.hour_from
    if args.hour_to is not None:
        mask &= df["pickup_hour"] <= args.hour_to
    if args.min_distance is not None:
        mask &= df["trip_distance"] >= args.min_distance
    if args.max_distance is not None:
        mask &= df["trip_distance"] <= args.max_distance
    if args.min_fare is not None:
        mask &= df["fare_amount"] >= args.min_fare
    if args.max_fare is not None:
        mask &= df["fare_amount"] <= args.max_fare
    if args.payment_type is not None:
        mask &= df["payment_type_id"] == args.payment_type
    return df[mask]


def main():
    args = parse_arguments()
    totals = {"trips": 0, "distance": 0.0, "fare": 0.0, "duration": 0.0, "speed": 0.0, "tip": 0.0, "tip_count": 0}
    hourly = {}
    hourly_fare = {}
    hourly_speed = {}
    boroughs = {}
    payments = {}
    distance_bins = {}
    columns = [
        "pickup_date", "pickup_borough", "pickup_hour", "trip_distance", "fare_amount", "payment_type_id",
        "duration_min", "avg_speed_mph", "tip_pct", "pickup_location_id", "dropoff_location_id",
    ]
    kept = []

    for df in iter_clean(columns=columns):
        df = apply_filters(df, args)
        totals["trips"] += len(df)
        totals["distance"] += float(df["trip_distance"].sum())
        totals["fare"] += float(df["fare_amount"].sum())
        totals["duration"] += float(df["duration_min"].sum())
        totals["speed"] += float(df["avg_speed_mph"].sum())
        totals["tip"] += float(df["tip_pct"].sum())
        totals["tip_count"] += int(df["tip_pct"].notna().sum())
        add_counts(hourly, df["pickup_hour"])
        for hour, group in df.groupby("pickup_hour"):
            key = str(hour)
            hourly_fare[key] = hourly_fare.get(key, 0.0) + float(group["fare_amount"].sum())
            hourly_speed[key] = hourly_speed.get(key, 0.0) + float(group["avg_speed_mph"].sum())
        add_counts(boroughs, df["pickup_borough"])
        add_counts(payments, df["payment_type_id"])
        add_counts(distance_bins, cut(df["trip_distance"], DISTANCE_BINS))
        kept.append(df[["pickup_location_id", "dropoff_location_id"]])

    n = totals["trips"]
    summary = {
        "trips": n,
        "avg_distance": round(totals["distance"] / n, 4) if n else 0,
        "avg_fare": round(totals["fare"] / n, 4) if n else 0,
        "avg_duration": round(totals["duration"] / n, 4) if n else 0,
        "avg_speed": round(totals["speed"] / n, 4) if n else 0,
        "avg_tip_pct": round(totals["tip"] / totals["tip_count"], 4) if totals["tip_count"] else 0,
    }

    def pairs():
        for frame in kept:
            for pickup, dropoff in zip(frame["pickup_location_id"].tolist(), frame["dropoff_location_id"].tolist()):
                yield pickup, dropoff

    zones = pd.read_csv(os.path.join(PROCESSED_DIR, "zones.csv"), keep_default_na=False)
    names = {int(r.location_id): r.zone for r in zones.itertuples()}
    routes = []
    for count, (pickup, dropoff) in top_k_routes(pairs(), args.k):
        routes.append({"pickup_zone": names[pickup], "dropoff_zone": names[dropoff], "trips": count})

    hours = []
    for hour in sorted(hourly, key=int):
        count = hourly[hour]
        hours.append({
            "hour": int(hour), "trips": count,
            "avg_fare": round(hourly_fare[hour] / count, 4),
            "avg_speed": round(hourly_speed[hour] / count, 4),
        })

    result = {
        "filters": {k: v for k, v in vars(args).items() if v is not None and k not in ("json", "k")},
        "summary": summary,
        "hourly": hours,
        "boroughs": dict(sorted(boroughs.items(), key=lambda item: -item[1])),
        "payment_types": dict(sorted(payments.items())),
        "distance_bins": {label: distance_bins.get(label, 0) for label in DISTANCE_BINS[1]},
        "top_routes": routes,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("Filters:", result["filters"] or "none")
    print()
    print("Summary (compare with /api/summary)")
    for key, value in summary.items():
        print("  {:<14} {}".format(key, value))
    print()
    print("Trips by hour (compare with /api/hourly)")
    print(pd.DataFrame(hours).to_string(index=False) if hours else "  no trips")
    print()
    print("Pickups by borough:", result["boroughs"])
    print("Trips by payment type id:", result["payment_types"])
    print("Trips by distance bin:", result["distance_bins"])
    print()
    print("Top {} routes".format(args.k))
    print(pd.DataFrame(routes).to_string(index=False) if routes else "  no trips")


if __name__ == "__main__":
    main()
