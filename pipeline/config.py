import glob
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOOKUP_CSV = os.path.join(RAW_DIR, "taxi_zone_lookup.csv")
ZONES_ZIP = os.path.join(RAW_DIR, "taxi_zones.zip")
CLEAN_PARQUET = os.path.join(PROCESSED_DIR, "trips_clean.parquet")


def find_trip_file():
    files = []
    for pattern in ["yellow_tripdata*.parquet", "yellow_tripdata*.csv"]:
        files.extend(glob.glob(os.path.join(RAW_DIR, pattern)))
    if not files:
        return None
    return sorted(files)[-1]
