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
| `python pipeline/clean_data.py` | removes bad rows in chunks of 500000 rows (low memory), writes the cleaned file and the exclusion logs |

All scripts accept `--file path/to/file` and `--max-rows 500000`. For `load_data.py` and `explore_quality.py` it is a random sample. For `clean_data.py` it means the first N rows of the file. `clean_data.py` also accepts `--chunk-size` (default 500000) if you want it to use even less memory.

## Output

- `data/processed/trips_clean.parquet`: cleaned and enriched trips (columns in `pipeline/FIELDS.md`)
- `logs/quality_report.txt`: problems found before cleaning
- `logs/exclusion_summary.csv`: how many rows each rule removed or fixed
- `logs/excluded_records.csv`: up to 500 example rows for every rule

## Cleaning rules

Rows are removed when they have: a missing important value, a duplicate, dropoff not after pickup, pickup outside the month of the file, duration under 1 or over 180 minutes, distance of 0 or over 100 miles, fare of 0 or over 500 dollars, total of 0 or over 1000 dollars, a negative tip or toll, a zone id that is not in the lookup, more than 6 passengers, or a speed above 80 mph.

Rows are kept but fixed when passenger count is missing or 0 (set to 1), or when rate code or payment type is missing (set to the unknown code).

The limits are at the top of `pipeline/rules.py` if the team wants to change them.
