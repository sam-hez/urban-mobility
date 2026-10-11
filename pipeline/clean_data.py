import argparse
import os
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config import CLEAN_PARQUET, LOG_DIR, PROCESSED_DIR, find_trip_file
from load_data import build_zone_table, count_pickup_months, enrich_trips, iter_trips, read_lookup, read_shapes
from reference import FEE_COLUMNS, MONEY_COLUMNS, PAYMENT_TYPES, RATE_CODES, VENDORS
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

STAT_COLUMNS = ["trip_distance", "fare_amount", "tip_amount", "total_amount", "duration_min", "passenger_count"]

NORMALIZE_DESCRIPTIONS = {
    "passenger_count_imputed": "Missing or zero passenger count set to 1",
    "vendor_imputed": "Missing or unknown vendor id set to 0 (unknown)",
    "rate_code_imputed": "Missing or unknown rate code set to 99 (unknown)",
    "payment_type_imputed": "Missing or unknown payment type set to 5 (unknown)",
    "store_flag_cleared": "Store and forward flag other than Y or N set to empty",
}
for fee in FEE_COLUMNS:
    NORMALIZE_DESCRIPTIONS[fee + "_filled"] = "Missing {} set to 0 (fee not charged or not recorded)".format(fee)


def new_stats():
    return {c: {"count": 0, "sum": 0.0, "min": None, "max": None} for c in STAT_COLUMNS}


def update_stats(stats, df):
    for column in STAT_COLUMNS:
        values = df[column].dropna()
        if values.empty:
            continue
        entry = stats[column]
        low = float(values.min())
        high = float(values.max())
        entry["count"] += len(values)
        entry["sum"] += float(values.sum())
        entry["min"] = low if entry["min"] is None else min(entry["min"], low)
        entry["max"] = high if entry["max"] is None else max(entry["max"], high)


def normalize(df, counts):
    mask = df["passenger_count"].isna() | (df["passenger_count"] == 0)
    counts["passenger_count_imputed"] += int(mask.sum())
    df.loc[mask, "passenger_count"] = 1

    mask = ~df["vendor_id"].isin(list(VENDORS))
    counts["vendor_imputed"] += int(mask.sum())
    df.loc[mask, "vendor_id"] = 0

    mask = ~df["rate_code_id"].isin(list(RATE_CODES))
    counts["rate_code_imputed"] += int(mask.sum())
    df.loc[mask, "rate_code_id"] = 99

    mask = ~df["payment_type_id"].isin(list(PAYMENT_TYPES))
    counts["payment_type_imputed"] += int(mask.sum())
    df.loc[mask, "payment_type_id"] = 5

    flag = df["store_and_fwd_flag"].astype("string").str.strip().str.upper()
    valid_flag = flag.isin(["Y", "N"])
    counts["store_flag_cleared"] += int((~valid_flag & df["store_and_fwd_flag"].notna()).sum())
    df["store_and_fwd_flag"] = flag.where(valid_flag)

    for fee in FEE_COLUMNS:
        df[fee] = pd.to_numeric(df[fee], errors="coerce")
        counts[fee + "_filled"] += int(df[fee].isna().sum())
        df[fee] = df[fee].fillna(0.0)
    return df


def fix_types(df):
    for column in INT_COLUMNS:
        df[column] = df[column].astype("int64")
    for column in FLOAT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("float64")
    for column in MONEY_COLUMNS + ["trip_distance", "duration_min"]:
        df[column] = df[column].round(2)
    df["store_and_fwd_flag"] = df["store_and_fwd_flag"].astype("string")
    return df


def stats_table(before, after):
    rows = []
    for column in STAT_COLUMNS:
        b = before[column]
        a = after[column]
        rows.append({
            "column": column,
            "count_before": b["count"],
            "count_after": a["count"],
            "mean_before": round(b["sum"] / b["count"], 3) if b["count"] else None,
            "mean_after": round(a["sum"] / a["count"], 3) if a["count"] else None,
            "min_before": b["min"],
            "min_after": a["min"],
            "max_before": b["max"],
            "max_after": a["max"],
        })
    return pd.DataFrame(rows)


def save_reference_tables(zones):
    zones.to_csv(os.path.join(PROCESSED_DIR, "zones.csv"), index=False)
    pd.DataFrame(list(VENDORS.items()), columns=["vendor_id", "vendor_name"]).to_csv(
        os.path.join(PROCESSED_DIR, "vendors.csv"), index=False)
    pd.DataFrame(list(RATE_CODES.items()), columns=["rate_code_id", "description"]).to_csv(
        os.path.join(PROCESSED_DIR, "rate_codes.csv"), index=False)
    pd.DataFrame(list(PAYMENT_TYPES.items()), columns=["payment_type_id", "description"]).to_csv(
        os.path.join(PROCESSED_DIR, "payment_types.csv"), index=False)


def write_report(path, main_period, input_rows, kept_rows, summary_frame, comparison):
    removed = input_rows - kept_rows
    lines = []
    lines.append("Cleaning report")
    lines.append("File: " + os.path.basename(path))
    lines.append("Main month: {}".format(main_period))
    lines.append("")
    lines.append("Rows before cleaning: {}".format(input_rows))
    lines.append("Rows removed:         {} ({:.2f}%)".format(removed, removed / input_rows * 100))
    lines.append("Rows after cleaning:  {}".format(kept_rows))
    lines.append("")
    lines.append("Rows removed by rule (each row is counted under the first rule it fails)")
    for row in summary_frame[summary_frame["action"] == "excluded"].itertuples():
        lines.append("  {:<26} {:>10}  {:>6.3f}%  {}".format(row.reason, row.record_count, row.percent_of_input, row.description))
    lines.append("")
    lines.append("Values fixed in rows that were kept")
    for row in summary_frame[summary_frame["action"] == "imputed"].itertuples():
        lines.append("  {:<26} {:>10}  {:>6.3f}%  {}".format(row.reason, row.record_count, row.percent_of_input, row.description))
    lines.append("")
    lines.append("Key numbers before and after cleaning")
    lines.append(comparison.to_string(index=False))
    lines.append("")
    with open(os.path.join(LOG_DIR, "cleaning_report.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


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
    normalize_counts = {name: 0 for name in NORMALIZE_DESCRIPTIONS}
    samples = []
    sample_totals = {}
    stats_before = new_stats()
    stats_after = new_stats()

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
        update_stats(stats_before, df)

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

        df = normalize(df.copy(), normalize_counts)
        df = df.drop(columns=["source_row"])
        df = fix_types(df)
        update_stats(stats_after, df)
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
    for name, description in NORMALIZE_DESCRIPTIONS.items():
        summary.append((name, "imputed", normalize_counts[name], description))

    summary_frame = pd.DataFrame(summary, columns=["reason", "action", "record_count", "description"])
    summary_frame.insert(3, "percent_of_input", (summary_frame["record_count"] / input_rows * 100).round(3))
    summary_frame.to_csv(os.path.join(LOG_DIR, "exclusion_summary.csv"), index=False)

    comparison = stats_table(stats_before, stats_after)
    comparison.to_csv(os.path.join(LOG_DIR, "before_after_summary.csv"), index=False)

    if samples:
        log = pd.concat(samples, ignore_index=True, sort=False)
    else:
        log = pd.DataFrame(columns=["reason"])
    log.to_csv(os.path.join(LOG_DIR, "excluded_records.csv"), index=False)

    write_report(path, main_period, input_rows, kept_rows, summary_frame, comparison)
    save_reference_tables(zones)

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
