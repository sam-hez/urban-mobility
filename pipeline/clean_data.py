import argparse
import os
import sys
from features import add_features

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config import CLEAN_PARQUET, LOG_DIR, PROCESSED_DIR, find_trip_file
from load_data import build_zone_table, count_pickup_months, enrich_trips, iter_trips, read_lookup, read_shapes
from rules import RULES, make_chunk_context, prepare

SAMPLE_PER_REASON = 500

INT_COLUMNS = [
    "vendor_id", "passenger_count", "rate_code_id", "pickup_location_id",
    "dropoff_location_id", "payment_type_id",
]

FLOAT_COLUMNS = [
    "trip_distance", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee", "duration_min",
]


def impute(df, counts):
    mask = df["passenger_count"].isna() | (df["passenger_count"] == 0)
    counts["passenger_count_imputed"] += int(mask.sum())
    df.loc[mask, "passenger_count"] = 1

    mask = df["rate_code_id"].isna()
    counts["rate_code_imputed"] += int(mask.sum())
    df.loc[mask, "rate_code_id"] = 99

    mask = df["payment_type_id"].isna()
    counts["payment_type_imputed"] += int(mask.sum())
    df.loc[mask, "payment_type_id"] = 5
    return df


def fix_types(df):
    for column in INT_COLUMNS:
        df[column] = df[column].astype("int64")
    for column in FLOAT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("float64")
    df["duration_min"] = df["duration_min"].round(2)
    df["store_and_fwd_flag"] = df["store_and_fwd_flag"].astype("string")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--max-rows", type=int, help="only use the first N rows of the file")
    parser.add_argument("--chunk-size", type=int, default=500000)
    args = parser.parse_args()

    path = args.file or find_trip_file()
    if not path or not os.path.exists(path):
        print("No yellow_tripdata file (.csv or .parquet) in data/raw/")
        print("Put the course file there or run: python pipeline/download_data.py")
        sys.exit(1)

    zones = build_zone_table(read_lookup(), read_shapes())

    print("Finding the main month of the file")
    month_counts = count_pickup_months(path, args.chunk_size, args.max_rows)
    main_period = max(month_counts, key=month_counts.get)
    print("Main month:", main_period)

    context = make_chunk_context(zones["location_id"], main_period)
    rule_counts = {name: 0 for name, _, _ in RULES}
    impute_counts = {
        "passenger_count_imputed": 0,
        "rate_code_imputed": 0,
        "payment_type_imputed": 0,
    }
    samples = []
    sample_totals = {}

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    writer = None
    input_rows = 0
    kept_rows = 0

    for chunk in iter_trips(path, args.chunk_size):
        if args.max_rows:
            room = args.max_rows - input_rows
            if room <= 0:
                break
            chunk = chunk.iloc[:room]

        df = prepare(chunk)
        df["source_row"] = np.arange(input_rows, input_rows + len(df))
        input_rows += len(df)

        for name, description, rule in RULES:
            mask = rule(df, context)
            count = int(mask.sum())
            rule_counts[name] += count
            already = sample_totals.get(name, 0)
            if count > 0 and already < SAMPLE_PER_REASON:
                sample = df[mask].head(SAMPLE_PER_REASON - already).copy()
                sample.insert(0, "reason", name)
                samples.append(sample)
                sample_totals[name] = already + len(sample)
            df = df[~mask]

        df = impute(df.copy(), impute_counts)
        df = df.drop(columns=["source_row"])
        df = fix_types(df)
        df = add_features(df)
        df = enrich_trips(df, zones)

        if len(df) > 0:
            table = pa.Table.from_pandas(df, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(CLEAN_PARQUET, table.schema)
            else:
                table = table.cast(writer.schema)
            writer.write_table(table)
            kept_rows += len(df)
        print("  rows read:", input_rows, "kept so far:", kept_rows)

    if writer is None:
        raise SystemExit("No rows were kept after cleaning")
    writer.close()

    summary = []
    for name, description, _ in RULES:
        summary.append((name, "excluded", rule_counts[name], description))
    summary.append(("passenger_count_imputed", "imputed", impute_counts["passenger_count_imputed"], "Missing or zero passenger count set to 1"))
    summary.append(("rate_code_imputed", "imputed", impute_counts["rate_code_imputed"], "Missing rate code set to 99 (unknown)"))
    summary.append(("payment_type_imputed", "imputed", impute_counts["payment_type_imputed"], "Missing payment type set to 5 (unknown)"))

    summary_frame = pd.DataFrame(summary, columns=["reason", "action", "record_count", "description"])
    summary_frame.insert(3, "percent_of_input", (summary_frame["record_count"] / input_rows * 100).round(3))
    summary_frame.to_csv(os.path.join(LOG_DIR, "exclusion_summary.csv"), index=False)

    if samples:
        log = pd.concat(samples, ignore_index=True, sort=False)
    else:
        log = pd.DataFrame(columns=["reason"])
    log.to_csv(os.path.join(LOG_DIR, "excluded_records.csv"), index=False)

    print()
    print("Rows read:", input_rows)
    for name, description, _ in RULES:
        print("  {:<26} removed {}".format(name, rule_counts[name]))
    removed = input_rows - kept_rows
    print()
    print("Rows kept:", kept_rows)
    print("Rows removed:", removed, "({:.2f}%)".format(removed / input_rows * 100))
    print("Cleaned file:", CLEAN_PARQUET)
    print("Logs written to:", LOG_DIR)


if __name__ == "__main__":
    main()
