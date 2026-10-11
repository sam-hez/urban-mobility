# Fields produced by the cleaning pipeline

File: `data/processed/trips_clean.parquet` (made by `python pipeline/clean_data.py`)

One row is one cleaned yellow taxi trip, already joined with the zone information for the pickup and the dropoff. Rows are in the same order as the original file (not sorted by time).

| Column | Type | Notes |
| --- | --- | --- |
| vendor_id | int | taxi technology vendor, unknown values set to 0 |
| pickup_datetime | datetime | cleaned, always inside the month of the file |
| dropoff_datetime | datetime | always after pickup |
| passenger_count | int | missing or 0 was set to 1 |
| trip_distance | float | miles, between 0 and 100 |
| rate_code_id | int | missing or unknown set to 99 |
| store_and_fwd_flag | text | Y or N, empty if it was something else |
| pickup_location_id | int | joins to zone lookup LocationID |
| dropoff_location_id | int | joins to zone lookup LocationID |
| payment_type_id | int | missing or unknown set to 5 |
| fare_amount | float | dollars, between 0 and 500 |
| extra | float | empty was set to 0.0 |
| mta_tax | float | empty was set to 0.0 |
| tip_amount | float | dollars, not negative |
| tolls_amount | float | dollars, not negative |
| improvement_surcharge | float | empty was set to 0.0 |
| total_amount | float | dollars, between 0 and 1000 |
| congestion_surcharge | float | empty was set to 0.0 |
| airport_fee | float | empty was set to 0.0 |
| duration_min | float | dropoff minus pickup in minutes, between 1 and 180 |
| pickup_borough | text | from taxi_zone_lookup |
| pickup_zone | text | from taxi_zone_lookup |
| pickup_service_zone | text | from taxi_zone_lookup |
| pickup_lat | float | centre of the zone polygon, empty for zones without polygon |
| pickup_lon | float | same as above |
| dropoff_borough | text | from taxi_zone_lookup |
| dropoff_zone | text | from taxi_zone_lookup |
| dropoff_service_zone | text | from taxi_zone_lookup |
| dropoff_lat | float | centre of the zone polygon, empty for zones without polygon |
| dropoff_lon | float | same as above |

## Reference tables

Saved next to the trips in `data/processed/`:

| File | Columns |
| --- | --- |
| zones.csv | location_id, borough, zone, service_zone, polygon_parts, centroid_lat, centroid_lon |
| vendors.csv | vendor_id, vendor_name |
| rate_codes.csv | rate_code_id, description |
| payment_types.csv | payment_type_id, description |

Every id in `trips_clean.parquet` exists in these tables, so they can be used as foreign keys. `python pipeline/validate_clean.py` checks this.

## Zone table

`load_data.build_zone_table()` gives one row per zone: location_id, borough, zone, service_zone, polygon_parts, centroid_lat, centroid_lon.

- 265 zones in the lookup file, 260 of them have a polygon.
- Zones 57, 104, 105, 264 and 265 have no polygon of their own.
- Zones 56 and 103 have more than one polygon in the shapefile, the largest one is used for the centre point.

## Not done yet

Derived features (speed, fare per mile, tip percentage, hour of day and so on) are not in this file. They are the next step after cleaning.
