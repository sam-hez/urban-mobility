import argparse
import os
import time
from urllib.parse import quote_plus

import pandas as pd
import pyarrow.parquet as pq
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
TRIPS_FILE = os.path.join(PROCESSED_DIR, "trips_clean.parquet")
SCHEMA_FILE = os.path.join(ROOT, "database", "schema.sql")
INDEX_FILE = os.path.join(ROOT, "database", "indexes.sql")

BATCH_SIZE = 50000

TRIP_COLUMNS = [
        "vendor_id", "pickup_datetime", "dropoff_datetime",
        "pickup_location_id", "dropoff_location_id",
        "rate_code_id", "payment_type_id", "passenger_count",
        "trip_distance", "store_and_fwd_flag",
        "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
        "improvement_surcharge", "congestion_surcharge", "airport_fee",
        "total_amount", "duration_min",
]

FEE_COLUMNS = ["extra", "mta_tax", "improvement_surcharge",
               "congestion_surcharge", "airport_fee"]

INSERT_TRIP_SQL = ("INSERT INTO trips (" + ", ".join(TRIP_COLUMNS) + ") VALUES ("
                    + ", ".join(["%s"] * len(TRIP_COLUMNS)) + ")")

TABLES = ["trips", "zones", "payment_types", "rate_codes",
          "vendors", "service_zones", "boroughs"]


def get_engine():    
    user = os.getenv("DB_USER")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME")
    return create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}")


def run_sql_file(engine, path):
    with open(path) as f:
        lines = f.read().splitlines()
    no_comments = "\n".join(line.split("--")[0] for line in lines)
    statements = [s.strip() for s in no_comments.split(";") if s.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
                                                      
                                                      
def create_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS " + ", ".join(TABLES)))
    run_sql_file(engine, SCHEMA_FILE)
                                                                                  
                                                                                  
def load_lookup_tables(engine):
    zones = pd.read_csv(os.path.join(PROCESSED_DIR, "zones.csv"),
                        keep_default_na=False, na_values=[""])

    pd.DataFrame({"borough_name": sorted(zones["borough"].unique())}) \
        .to_sql("boroughs", engine, if_exists="append", index=False)
    pd.DataFrame({"service_zone_name": sorted(zones["service_zone"].unique())}) \
        .to_sql("service_zones", engine, if_exists="append", index=False)

    boroughs = pd.read_sql("SELECT borough_id, borough_name FROM boroughs", engine)
    services = pd.read_sql("SELECT service_zone_id, service_zone_name FROM service_zones", engine)
    borough_ids = dict(zip(boroughs["borough_name"], boroughs["borough_id"]))
    service_ids = dict(zip(services["service_zone_name"], services["service_zone_id"]))
    
    pd.DataFrame({
        "location_id": zones["location_id"],
        "zone_name": zones["zone"],
        "borough_id": zones["borough"].map(borough_ids),
        "service_zone_id": zones["service_zone"].map(service_ids),
        "polygon_parts": zones["polygon_parts"],
        "centroid_lat": zones["centroid_lat"],
        "centroid_lon": zones["centroid_lon"],
    }).to_sql("zones", engine, if_exists="append", index=False)
    
    for table in ["vendors", "rate_codes", "payment_types"]:
        pd.read_csv(os.path.join(PROCESSED_DIR, table + ".csv")) \
            .to_sql(table, engine, if_exists="append", index=False)


def prepare_batch(df):
    df[FEE_COLUMNS] = df[FEE_COLUMNS].fillna(0.0)
    flag = df["store_and_fwd_flag"]
    df["store_and_fwd_flag"] = flag.where(flag.isin(["Y", "N"]), None)
    df = df.astype(object).where(df.notna(), None)
    return list(df.itertuples(index=False, name=None))


def load_trips(engine, limit=None):
    parquet = pq.ParquetFile(TRIPS_FILE)
    wanted = parquet.metadata.num_rows
    if limit:
        wanted = min(wanted, limit)

    loaded = 0
    started = time.time()
    connection = engine.raw_connection()   
    try:
        cursor = connection.cursor()
        for number, batch in enumerate(parquet.iter_batches(batch_size=BATCH_SIZE,
                                                            columns=TRIP_COLUMNS), start=1):
            df = batch.to_pandas()
            if limit and loaded + len(df) > limit:
                df = df.head(limit - loaded)
            rows = prepare_batch(df)
            try:
                cursor.executemany(INSERT_TRIP_SQL, rows)
                connection.commit()
            except Exception as error:
                connection.rollback()
                print(f"Batch {number} failed (rows {loaded + 1} to {loaded + len(rows)}):")
                print(error)
                raise            
            loaded += len(rows)
            print(f"  loaded {loaded:,} / {wanted:,} trips ({time.time() - started:.0f}s)")
            if limit and loaded >= limit:
                break    
    finally:
        connection.close()


def print_counts(engine):
    print("Row counts:")
    with engine.connect() as conn:
        for table in reversed(TABLES):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count:,}")


def main():
    parser = argparse.ArgumentParser(description="Load cleaned taxi data into MySQL")
    parser.add_argument("--limit", type=int, default=None,
                        help="only load the first N trips (for testing)")
    args = parser.parse_args()

    if not os.path.exists(TRIPS_FILE):
        raise SystemExit(f"Cleaned file not found: {TRIPS_FILE}")

    engine = get_engine()
    begin = time.time()

    print("1/4 Creating tables...")
    create_tables(engine)
    print("2/4 Loading lookup tables...")
    load_lookup_tables(engine)
    print("3/4 Loading trips...")
    load_trips(engine, args.limit)
    print("4/4 Creating indexes...")
    run_sql_file(engine, INDEX_FILE)

    print_counts(engine)
    print(f"Done in {time.time() - begin:.0f} seconds.")


if __name__ == "__main__":
    main()
