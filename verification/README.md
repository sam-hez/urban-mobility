# Final data verification

Three tools that check the application against the cleaned dataset. Run them from the project folder with the venv active.

## 1. Compare MySQL with the cleaned dataset

```
python3 verification/verify_mysql.py --database YOUR_DATABASE --user YOUR_USER
```

It asks for the password (or reads `MYSQL_PASSWORD`). Options:

| Option | Meaning |
| --- | --- |
| `--host`, `--port` | default 127.0.0.1 and 3306 |
| `--trips-table`, `--zones-table` | table names, default `trips` and `zones` |
| `--zone-id-column`, `--zone-name-column` | columns of the zones table, default `location_id`, name check is skipped if not given |
| `--map standard=actual` | use when a column has another name in MySQL, for example `--map pickup_location_id=PULocationID` (repeat it for each column) |
| `--check-duplicates` | also looks for duplicate trips, slow on millions of rows |
| `--skip-algorithm` | skips the top routes check |

The standard column names are the ones in `pipeline/FIELDS.md`.

### What it checks

| Section | Checks |
| --- | --- |
| Row counts | trips table and zones table against the cleaned file, trips per day |
| Invalid data | no distance, fare, total, tip, duration, passenger, speed or month outside the cleaning limits, dropoff after pickup |
| Zone mapping | every pickup and dropoff id exists in the zones table, zone ids and names match `zones.csv`, trips per zone match |
| Nulls | the null count of every column matches the cleaned file |
| Engineered fields | speed, fare per mile, tip percent, pickup date, hour, weekday, weekend flag and time period are recalculated in SQL and must match |
| Distributions | sums, minimums and maximums, and trips by hour, weekday, payment type, vendor, rate code, time period, distance, fare and speed range must match. Warns about quiet days, hours with no trips and one zone holding over 20% of trips |
| Algorithm | the hand-written top 10 routes must equal a pandas baseline and a MySQL `GROUP BY` |

Results are printed as PASS, FAIL, WARN, SKIP or INFO and saved to `logs/database_verification.txt` and `logs/database_verification.csv`. The script exits with an error if anything fails.

SKIP means a column is not in the MySQL trips table (for example a derived field that the API calculates instead). Check it through the API with tool 2.

### Reading the result

- A row count that is lower or higher means rows were lost or loaded twice.
- A failure in Invalid data means rows that should have been cleaned got into MySQL.
- A failure in Zone mapping usually means an id was loaded wrongly.
- A null count that differs by a few rows often comes from the text `N/A` (zones 264 and 265 have `N/A` as borough or service zone). pandas turns `N/A` into a missing value unless `keep_default_na=False` is used when the csv is read.

## 2. Expected values for the API

```
python3 verification/expected_values.py --borough Manhattan --hour-from 7 --hour-to 9 --payment-type 1
```

It prints what the API should return for the same filters, calculated straight from the cleaned file: the summary, trips by hour, pickups by borough, payment types, distance ranges and the top routes. Add `--json` for JSON. The filter options have the same names as the dashboard filters (`--start-date`, `--end-date`, `--borough`, `--hour-from`, `--hour-to`, `--min-distance`, `--max-distance`, `--min-fare`, `--max-fare`, `--payment-type`, `--k`).

Try a few filter sets, call the API with the same filters and compare the numbers. Small differences in the last decimal come from rounding.

## 3. Observations for the report

```
python3 verification/observations.py
```

It prints tables for hours, weekdays and weekends, boroughs, distance ranges, tips, airports and the top routes, and writes `logs/observations.txt` with four candidate observations. Pick three, check each one in the running dashboard, and explain what it means for urban mobility.
