import argparse
import os
import sys
import tempfile
import zipfile

import pandas as pd
import pyarrow.parquet as pq
import shapefile

from config import LOOKUP_CSV, ZONES_ZIP, find_trip_file
from load_data import build_zone_table, join_coverage, read_lookup, read_shapes, read_trips


def show_trip_file(path):
    print("=== Trip data ===")
    print("File:", os.path.basename(path))
    if path.lower().endswith(".csv"):
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            rows = sum(1 for _ in handle) - 1
        sample = pd.read_csv(path, nrows=100000, low_memory=False)
        print("Format: csv")
        print("Rows:", rows)
        print()
        print("{:<24} {}".format("column", "type (guessed from first 100000 rows)"))
        for name, dtype in sample.dtypes.items():
            print("{:<24} {}".format(name, dtype))
        print()
        print("First rows")
        print(sample.head(3).to_string(index=False))
    else:
        parquet = pq.ParquetFile(path)
        print("Format: parquet")
        print("Rows:", parquet.metadata.num_rows)
        print("Row groups:", parquet.metadata.num_row_groups)
        print()
        print("{:<24} {}".format("column", "type"))
        for field in parquet.schema_arrow:
            print("{:<24} {}".format(field.name, field.type))
    print()


def show_lookup():
    print("=== Zone lookup (csv) ===")
    raw = pd.read_csv(LOOKUP_CSV, keep_default_na=False)
    print("Rows:", len(raw))
    print("Columns:", list(raw.columns))
    print("LocationID range:", raw["LocationID"].min(), "to", raw["LocationID"].max())
    print("Duplicate LocationIDs:", int(raw["LocationID"].duplicated().sum()))
    print()
    print("Zones per borough")
    print(raw["Borough"].value_counts().to_string())
    print()
    print("Zones per service zone")
    print(raw["service_zone"].value_counts().to_string())
    print()
    print("Special ids")
    print(raw[raw["Borough"].isin(["Unknown", "N/A"])].to_string(index=False))
    print()


def show_shapes():
    print("=== Zone shapes (shapefile) ===")
    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(ZONES_ZIP) as archive:
            print("Files in zip:", [n for n in archive.namelist()])
            archive.extractall(folder)
        reader = shapefile.Reader(os.path.join(folder, "taxi_zones"))
        print("Shape type:", reader.shapeTypeName)
        print("Shapes:", len(reader))
        print("Bounding box:", [round(v) for v in reader.bbox])
        print("Fields:", [(f[0], f[1]) for f in reader.fields[1:]])
        with open(os.path.join(folder, "taxi_zones.prj"), "r") as handle:
            print("Projection:", handle.read()[:70], "...")
        names = [f[0] for f in reader.fields[1:]]
        ids = [int(r[names.index("LocationID")]) for r in reader.records()]
        repeated = sorted(set(i for i in ids if ids.count(i) > 1))
        print("LocationIDs with more than one polygon:", repeated)
        reader.close()
    print()


def show_join_keys(path):
    print("=== Join keys ===")
    print("trips.PULocationID  -> zone lookup.LocationID -> shapefile.LocationID")
    print("trips.DOLocationID  -> zone lookup.LocationID -> shapefile.LocationID")
    trips = read_trips(path, max_rows=200000)
    zones = build_zone_table(read_lookup(), read_shapes())
    print("Checked on up to 200000 trip rows")
    for key, value in join_coverage(trips, zones).items():
        print(" ", key, "=", value)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    args = parser.parse_args()
    path = args.file or find_trip_file()
    if not path or not os.path.exists(path):
        print("No yellow_tripdata file (.csv or .parquet) in data/raw/")
        print("Put the course file there or run: python pipeline/download_data.py")
        sys.exit(1)
    show_trip_file(path)
    show_lookup()
    show_shapes()
    show_join_keys(path)


if __name__ == "__main__":
    main()
