import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")

DB_PATH = os.path.join(DATA_DIR, "mobility.db")
GEOJSON_PATH = os.path.join(PROCESSED_DIR, "zones.geojson")
CLEANING_SUMMARY_PATH = os.path.join(LOG_DIR, "exclusion_summary.csv")

HOST = "127.0.0.1"
PORT = 5000
