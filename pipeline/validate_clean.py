import argparse
import os
import sys

import pandas as pd
import pyarrow.parquet as pq

from config import CLEAN_PARQUET, LOG_DIR
from reference import FEE_COLUMNS, PAYMENT_TYPES, RATE_CODES, VENDORS
from rules import (
    CRITICAL, MAX_DISTANCE, MAX_DURATION, MAX_FARE, MAX_PASSENGERS, MAX_SPEED, MAX_TIP, MAX_TOTAL, MIN_DURATION,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=CLEAN_PARQUET)
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print("Cleaned file not found. Run: python pipeline/clean_data.py")
        sys.exit(1)

    zone_ids = set(pd.read_csv(os.path.join(os.path.dirname(args.file), "zones.csv"))["location_id"])
    parquet = pq.ParquetFile(args.file)
    names = parquet.schema_arrow.names

    failures = {}
    months = set()
    total_rows = 0

    def fail(check, count):
        if count > 0:
            failures[check] = failures.get(check, 0) + int(count)

    for batch in parquet.iter_batches(batch_size=500000):
        df = batch.to_pandas()
        total_rows += len(df)
        hours = (df["dropoff_datetime"] - df["pickup_datetime"]).dt.total_seconds() / 3600

        fail("missing critical values", df[CRITICAL].isna().sum().sum())
        fail("dropoff not after pickup", (df["dropoff_datetime"] <= df["pickup_datetime"]).sum())
        months.update(df["pickup_datetime"].dt.to_period("M").unique())
        fail("duration outside range", ((hours * 60 < MIN_DURATION) | (hours * 60 > MAX_DURATION)).sum())
        fail("distance outside range", ((df["trip_distance"] <= 0) | (df["trip_distance"] > MAX_DISTANCE)).sum())
        fail("fare outside range", ((df["fare_amount"] <= 0) | (df["fare_amount"] > MAX_FARE)).sum())
        fail("total outside range", ((df["total_amount"] <= 0) | (df["total_amount"] > MAX_TOTAL)).sum())
        fail("tip above limit", (df["tip_amount"] > MAX_TIP).sum())
        fail("total below fare", (df["total_amount"] < df["fare_amount"]).sum())
        fail("negative tip or tolls", ((df["tip_amount"] < 0) | (df["tolls_amount"] < 0)).sum())
        fail("passenger count outside range", ((df["passenger_count"] < 1) | (df["passenger_count"] > MAX_PASSENGERS)).sum())
        fail("speed above limit", ((df["trip_distance"] / hours) > MAX_SPEED).sum())
        fail("unknown vendor id", (~df["vendor_id"].isin(list(VENDORS))).sum())
        fail("unknown rate code", (~df["rate_code_id"].isin(list(RATE_CODES))).sum())
        fail("unknown payment type", (~df["payment_type_id"].isin(list(PAYMENT_TYPES))).sum())
        fail("unknown pickup zone", (~df["pickup_location_id"].isin(zone_ids)).sum())
        fail("unknown dropoff zone", (~df["dropoff_location_id"].isin(zone_ids)).sum())
        fail("store flag not Y, N or empty", (df["store_and_fwd_flag"].notna() & ~df["store_and_fwd_flag"].isin(["Y", "N"])).sum())
        fail("empty fee columns", df[FEE_COLUMNS].isna().sum().sum())
        fail("zone name missing", (df["pickup_zone"].isna() | df["dropoff_zone"].isna()).sum())

    if len(months) > 1:
        failures["more than one month"] = len(months)

    lines = []
    lines.append("Validation of {}".format(os.path.basename(args.file)))
    lines.append("Rows checked: {}".format(total_rows))
    lines.append("Columns: {}".format(len(names)))
    lines.append("Months in pickup times: {}".format(sorted(str(m) for m in months)))
    lines.append("")
    if failures:
        lines.append("FAILED")
        for check, count in failures.items():
            lines.append("  {:<32} {}".format(check, count))
    else:
        lines.append("PASSED: every check found 0 problems")
    text = "\n".join(lines)
    print(text)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "validation_report.txt"), "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
