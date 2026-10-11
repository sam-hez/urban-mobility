# Urban Mobility Data Explorer: data pipeline

This part reads the three NYC TLC components, joins them and does the first cleaning.

| Component | File | Join key |
| --- | --- | --- |
| Trip records (fact) | course file `data/raw/yellow_tripdata_2019-01.csv` | PULocationID and DOLocationID |
| Zone lookup (dimension) | `data/raw/taxi_zone_lookup.csv` | LocationID |
| Zone shapes (spatial) | `data/raw/taxi_zones.zip` | LocationID |

## Setup

```
python -m venv venv
venv\Scripts\activate          (Windows)
source venv/bin/activate       (Mac and Linux)
pip install -r requirements.txt
```

## Get the trip data

The whole team uses the yellow_tripdata csv file from the course (the fact table).

1. Save it in `data/raw/`. The file name must start with `yellow_tripdata` (for example `yellow_tripdata.csv`).
2. Do not open it in Excel and save it again, that can change the dates and cut rows.

The scripts read the csv directly. The file is not committed to git because it is too big, so every teammate puts their own copy in `data/raw/`.


A parquet file from https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page also works if it is saved in `data/raw/` with a name starting `yellow_tripdata`. `python pipeline/download_data.py` downloads one.

## Scripts

Run them from the project folder, in this order.

| Command | What it does |
| --- | --- |
| `python pipeline/inspect_data.py` | prints the trip file columns, the lookup table, the shapefile details and the join key check |
| `python pipeline/load_data.py` | loads all three datasets and joins zone details to every trip |
| `python pipeline/explore_quality.py` | counts missing values, duplicates and invalid records, writes `logs/quality_report.txt` |
| `python pipeline/clean_data.py` | removes bad rows in chunks of 500000 rows (low memory), fixes and normalizes values, writes the cleaned file, the reference tables and the logs |
| `python pipeline/validate_clean.py` | checks the cleaned file against every rule and writes `logs/validation_report.txt` |

All scripts accept `--file path/to/file` and `--max-rows 500000`. For `load_data.py` and `explore_quality.py` it is a random sample. For `clean_data.py` it means the first N rows of the file. `clean_data.py` also accepts `--chunk-size` (default 500000) if you want it to use even less memory.

## Output

- `data/processed/trips_clean.parquet`: cleaned and enriched trips (columns in `pipeline/FIELDS.md`)
- `data/processed/zones.csv`, `vendors.csv`, `rate_codes.csv`, `payment_types.csv`: reference tables for the database
- `logs/cleaning_report.txt`: rows before and after, removals by rule, fixes, and key numbers before and after
- `logs/before_after_summary.csv`: the same key numbers as a table
- `logs/exclusion_summary.csv`: how many rows each rule removed or fixed
- `logs/excluded_records.csv`: up to 500 example rows for every rule
- `logs/quality_report.txt`: problems found before cleaning
- `logs/validation_report.txt`: result of the final check

## Cleaning rules

The full list with limits and reasons is in `pipeline/CLEANING_RULES.md`. The limits are at the top of `pipeline/rules.py`.
