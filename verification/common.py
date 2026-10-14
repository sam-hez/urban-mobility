import os
import sys

import pandas as pd
import pyarrow.parquet as pq

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "pipeline"))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from config import CLEAN_PARQUET, LOG_DIR, PROCESSED_DIR

DISTANCE_BINS = ([0, 1, 3, 5, 10, 20, float("inf")], ["0-1", "1-3", "3-5", "5-10", "10-20", "20+"])
FARE_BINS = ([0, 5, 10, 15, 25, 50, float("inf")], ["0-5", "5-10", "10-15", "15-25", "25-50", "50+"])
SPEED_BINS = ([0, 5, 10, 15, 20, 30, float("inf")], ["0-5", "5-10", "10-15", "15-20", "20-30", "30+"])


def iter_clean(columns=None, batch_size=500000):
    if not os.path.exists(CLEAN_PARQUET):
        raise SystemExit("Cleaned file not found. Run: python3 pipeline/clean_data.py")
    parquet = pq.ParquetFile(CLEAN_PARQUET)
    for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        yield batch.to_pandas()


def parquet_columns():
    return pq.ParquetFile(CLEAN_PARQUET).schema_arrow.names


def cut(series, bins):
    edges, labels = bins
    return pd.cut(series, bins=edges, labels=labels, right=False).astype(str)


def add_bins(df):
    df["distance_bin"] = cut(df["trip_distance"], DISTANCE_BINS)
    df["fare_bin"] = cut(df["fare_amount"], FARE_BINS)
    df["speed_bin"] = cut(df["avg_speed_mph"], SPEED_BINS)
    return df


def case_sql(column, bins):
    edges, labels = bins
    parts = []
    for i in range(len(labels) - 1):
        parts.append("WHEN {} < {} THEN '{}'".format(column, edges[i + 1], labels[i]))
    return "CASE " + " ".join(parts) + " ELSE '" + labels[-1] + "' END"


def add_counts(target, series):
    for key, count in series.value_counts().items():
        key = str(key)
        target[key] = target.get(key, 0) + int(count)
