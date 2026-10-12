# Database Requirements

Sources: `pipeline/FIELDS.md` and `pipeline/rules.py`.
The cleaning pipeline's validation script (`pipeline/validate_clean.py`) checks every row of the
cleaned file against these rules, so the database can rely on them.

## Trip fields (one row = one cleaned yellow taxi trip)
| Field | Type | NULL allowed? | Guaranteed range or rule |
|---|---|---|---|
| vendor_id | int | no | unknown values set to 0; exists in vendors.csv |
| pickup_datetime | datetime | no | inside the month of the file |
| dropoff_datetime | datetime | no | after pickup |
| passenger_count | int | no | 1 to 6 (0 or missing was set to 1) |
| trip_distance | float | no | above 0, at most 100 miles |
| rate_code_id | int | no | missing or unknown set to 99; exists in rate_codes.csv |
| payment_type_id | int | no | missing or unknown set to 5; exists in payment_types.csv |
| store_and_fwd_flag | text | YES | Y, N or empty |
| pickup_location_id | int | no | exists in zones.csv |
| dropoff_location_id | int | no | exists in zones.csv |
| fare_amount | float | no | above 0, at most 500 |
| extra, mta_tax, improvement_surcharge, congestion_surcharge, airport_fee | float | no | empty values set to 0.0 |
| tip_amount | float | no | 0 to 500 |
| tolls_amount | float | no | not negative |
| total_amount | float | no | above 0, at most 1000, not below fare_amount |
| duration_min | float | no | 1 to 180 minutes |

## Reference tables (in data/processed/)
| File | Columns |
|---|---|
| zones.csv | location_id, borough, zone, service_zone, polygon_parts, centroid_lat, centroid_lon |
| vendors.csv | vendor_id, vendor_name |
| rate_codes.csv | rate_code_id, description |
| payment_types.csv | payment_type_id, description |

## Parquet columns that are NOT stored in the trips table
pickup_ and dropoff_ borough, zone, service_zone, lat, lon.
They depend only on the zone id, so they are stored once in `zones` instead of
repeated in millions of trip rows.

## Facts the load script must handle
- 'N/A' and 'Unknown' are real text values in borough and service_zone, not missing data.
- An empty store_and_fwd_flag must be stored as NULL.
- 5 zones (57, 104, 105, 264, 265) have no polygon, so their centroid is NULL.
- The cleaned file is large (about 7.5 million rows), so it must be loaded in batches.
- Derived features are not part of the cleaned file yet.

## Open questions for the team
- Where is the final cleaned parquet shared (it is not in git)?
- Which derived features will be added, and when?
- Does the frontend need zone polygons, or are centroids enough?