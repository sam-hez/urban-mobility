import argparse
import os

import pandas as pd

from config import LOG_DIR
from load_data import load_all
from rules import RULES, make_context, prepare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    trips, zones, enriched, path = load_all(args.file, args.max_rows)
    df = prepare(enriched)
    context = make_context(df, zones["location_id"])
    total = len(df)

    lines = []
    lines.append("Data quality report")
    lines.append("File: " + os.path.basename(path))
    lines.append("Rows: {}".format(total))
    lines.append("Main month in file: {}".format(context["main_period"]))
    lines.append("")

    lines.append("Missing values per column")
    missing = df.isna().sum()
    for column, count in missing.items():
        if count > 0:
            lines.append("  {:<26} {:>10}  {:>6.2f}%".format(column, count, count / total * 100))
    if missing.sum() == 0:
        lines.append("  none")
    lines.append("")

    lines.append("Duplicates")
    lines.append("  Fully identical rows:          {}".format(int(trips.duplicated().sum())))
    lines.append("  Same key columns as earlier:   {}".format(int(df.duplicated(subset=["vendor_id", "pickup_datetime", "dropoff_datetime", "pickup_location_id", "dropoff_location_id", "trip_distance", "fare_amount", "total_amount"]).sum())))
    lines.append("")

    lines.append("Rows flagged by each rule (a row can be flagged by more than one)")
    for name, description, rule in RULES:
        count = int(rule(df, context).sum())
        lines.append("  {:<26} {:>10}  {:>6.2f}%  {}".format(name, count, count / total * 100, description))
    zero_passengers = int((df["passenger_count"].isna() | (df["passenger_count"] == 0)).sum())
    lines.append("  {:<26} {:>10}  {:>6.2f}%  {}".format("passenger_count_zero_or_missing", zero_passengers, zero_passengers / total * 100, "Not removed, set to 1 later"))
    lines.append("")

    lines.append("Summary of key numbers")
    summary = df[["trip_distance", "fare_amount", "total_amount", "duration_min", "passenger_count"]].describe().round(2)
    lines.append(summary.to_string())
    lines.append("")

    text = "\n".join(lines)
    print(text)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "quality_report.txt"), "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


if __name__ == "__main__":
    main()
