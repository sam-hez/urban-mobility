import argparse
import os
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapefile
from pyproj import Transformer

from config import LOOKUP_CSV, ZONES_ZIP, find_trip_file

CORE_COLUMNS = {
    "vendorid": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "ratecodeid": "rate_code_id",
    "pulocationid": "pickup_location_id",
    "dolocationid": "dropoff_location_id",
    "payment_type": "payment_type_id",
    "fare_amount": "fare_amount",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "total_amount": "total_amount",
}

OPTIONAL_COLUMNS = {
    "store_and_fwd_flag": "store_and_fwd_flag",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "improvement_surcharge": "improvement_surcharge",
    "congestion_surcharge": "congestion_surcharge",
    "airport_fee": "airport_fee",
}

TEXT_OPTIONAL = ["store_and_fwd_flag"]


KNOWN_COLUMNS = set(CORE_COLUMNS) | set(OPTIONAL_COLUMNS)


def column_mapping(names):
    wanted = {}
    for name in names:
        key = name.strip().lower()
        if key in CORE_COLUMNS:
            wanted[name] = CORE_COLUMNS[key]
        elif key in OPTIONAL_COLUMNS:
            wanted[name] = OPTIONAL_COLUMNS[key]
    return wanted


def parse_dates(series):
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().sum() > series.isna().sum() + len(series) * 0.01:
        parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    return parsed


def standardize_trips(trips, wanted, is_csv):
    missing = [c for c in CORE_COLUMNS.values() if c not in wanted.values()]
    if missing:
        raise SystemExit("Trip file is missing columns: " + ", ".join(missing))
    trips = trips.rename(columns=wanted)
    if is_csv:
        trips["pickup_datetime"] = parse_dates(trips["pickup_datetime"])
        trips["dropoff_datetime"] = parse_dates(trips["dropoff_datetime"])
    for column in OPTIONAL_COLUMNS.values():
        if column not in trips.columns:
            trips[column] = None if column in TEXT_OPTIONAL else np.nan
    return trips


def read_trips(path, max_rows=None):
    is_csv = path.lower().endswith(".csv")
    if is_csv:
        trips = pd.read_csv(path, usecols=lambda c: c.strip().lower() in KNOWN_COLUMNS, low_memory=False)
        wanted = column_mapping(trips.columns)
    else:
        names = pq.ParquetFile(path).schema_arrow.names
        wanted = column_mapping(names)
        trips = pd.read_parquet(path, columns=list(wanted.keys()))
    trips = standardize_trips(trips, wanted, is_csv)
    if max_rows and len(trips) > max_rows:
        trips = trips.sample(n=max_rows, random_state=42).reset_index(drop=True)
    return trips


def iter_trips(path, chunk_size=500000):
    if path.lower().endswith(".csv"):
        reader = pd.read_csv(
            path,
            usecols=lambda c: c.strip().lower() in KNOWN_COLUMNS,
            chunksize=chunk_size,
            low_memory=False,
        )
        for chunk in reader:
            yield standardize_trips(chunk, column_mapping(chunk.columns), True)
    else:
        parquet = pq.ParquetFile(path)
        wanted = column_mapping(parquet.schema_arrow.names)
        for batch in parquet.iter_batches(batch_size=chunk_size, columns=list(wanted.keys())):
            yield standardize_trips(batch.to_pandas(), wanted, False)


def count_pickup_months(path, chunk_size=500000, max_rows=None):
    pickup_name = "tpep_pickup_datetime"
    if path.lower().endswith(".csv"):
        reader = pd.read_csv(path, usecols=lambda c: c.strip().lower() == pickup_name, chunksize=chunk_size)
        series_chunks = (chunk.iloc[:, 0] for chunk in reader)
    else:
        parquet = pq.ParquetFile(path)
        real_name = [n for n in parquet.schema_arrow.names if n.lower() == pickup_name][0]
        batches = parquet.iter_batches(batch_size=chunk_size, columns=[real_name])
        series_chunks = (batch.to_pandas().iloc[:, 0] for batch in batches)

    counts = {}
    seen = 0
    for series in series_chunks:
        if max_rows:
            series = series.iloc[:max_rows - seen]
        months = parse_dates(series).dt.to_period("M").value_counts()
        for period, count in months.items():
            counts[period] = counts.get(period, 0) + int(count)
        seen += len(series)
        if max_rows and seen >= max_rows:
            break
    return counts


def read_lookup():
    lookup = pd.read_csv(LOOKUP_CSV, keep_default_na=False)
    lookup = lookup.rename(columns={
        "LocationID": "location_id",
        "Borough": "borough",
        "Zone": "zone",
        "service_zone": "service_zone",
    })
    for column in ["borough", "zone", "service_zone"]:
        lookup[column] = lookup[column].astype(str).str.strip()
    return lookup


def read_shapes():
    transformer = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(ZONES_ZIP) as archive:
            archive.extractall(folder)
        reader = shapefile.Reader(os.path.join(folder, "taxi_zones"))
        names = [f[0] for f in reader.fields[1:]]
        for item in reader.iterShapeRecords():
            record = dict(zip(names, item.record))
            min_x, min_y, max_x, max_y = item.shape.bbox
            lon, lat = transformer.transform((min_x + max_x) / 2, (min_y + max_y) / 2)
            rows.append({
                "location_id": int(record["LocationID"]),
                "shape_zone": record["zone"],
                "shape_borough": record["borough"],
                "shape_area": float(record["Shape_Area"]),
                "polygon_parts": len(item.shape.parts),
                "centroid_lat": round(lat, 5),
                "centroid_lon": round(lon, 5),
            })
        reader.close()
    shapes = pd.DataFrame(rows)
    shapes = shapes.sort_values("shape_area", ascending=False)
    shapes = shapes.drop_duplicates(subset="location_id", keep="first")
    return shapes.sort_values("location_id").reset_index(drop=True)


def build_zone_table(lookup, shapes):
    keep = shapes[["location_id", "polygon_parts", "centroid_lat", "centroid_lon"]]
    return lookup.merge(keep, on="location_id", how="left")


def enrich_trips(trips, zones):
    pickup = zones.rename(columns={
        "location_id": "pickup_location_id",
        "borough": "pickup_borough",
        "zone": "pickup_zone",
        "service_zone": "pickup_service_zone",
        "centroid_lat": "pickup_lat",
        "centroid_lon": "pickup_lon",
    }).drop(columns=["polygon_parts"])
    dropoff = zones.rename(columns={
        "location_id": "dropoff_location_id",
        "borough": "dropoff_borough",
        "zone": "dropoff_zone",
        "service_zone": "dropoff_service_zone",
        "centroid_lat": "dropoff_lat",
        "centroid_lon": "dropoff_lon",
    }).drop(columns=["polygon_parts"])
    enriched = trips.merge(pickup, on="pickup_location_id", how="left")
    enriched = enriched.merge(dropoff, on="dropoff_location_id", how="left")
    return enriched


def join_coverage(trips, zones):
    zone_ids = set(zones["location_id"])
    pickup_missing = ~trips["pickup_location_id"].isin(zone_ids)
    dropoff_missing = ~trips["dropoff_location_id"].isin(zone_ids)
    return {
        "trip_rows": len(trips),
        "pickup_ids_not_in_lookup": int(pickup_missing.sum()),
        "dropoff_ids_not_in_lookup": int(dropoff_missing.sum()),
        "zones_without_polygon": zones.loc[zones["centroid_lat"].isna(), "location_id"].tolist(),
    }


def load_all(path=None, max_rows=None):
    path = path or find_trip_file()
    if not path or not os.path.exists(path):
        print("No yellow_tripdata file (.csv or .parquet) in data/raw/")
        print("Put the course file there or run: python pipeline/download_data.py")
        sys.exit(1)
    trips = read_trips(path, max_rows)
    lookup = read_lookup()
    shapes = read_shapes()
    zones = build_zone_table(lookup, shapes)
    enriched = enrich_trips(trips, zones)
    return trips, zones, enriched, path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    trips, zones, enriched, path = load_all(args.file, args.max_rows)
    print("Trip file:", path)
    print("Trips loaded:", len(trips))
    print("Zones in lookup:", len(zones))
    print("Enriched columns:", len(enriched.columns))
    print()
    print("Join coverage")
    for key, value in join_coverage(trips, zones).items():
        print(" ", key, "=", value)
    print()
    print(enriched[[
        "pickup_datetime", "pickup_zone", "pickup_borough",
        "dropoff_zone", "dropoff_borough", "trip_distance", "fare_amount",
    ]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
