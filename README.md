# Urban Mobility Data Explorer

A web application that explores yellow taxi trips in New York City for January 2019. It cleans the official TLC data, stores it in MySQL, serves it through a Flask API and shows patterns in time, place and fares on an interactive dashboard.

- **Video walkthrough:** https://drive.google.com/drive/folders/1dzm_Kt-q5SeBAS5cxXOiqn3UQkaUXOdK?usp=sharing
- **Team participation sheet:** https://docs.google.com/spreadsheets/d/10EPXHb65T3EtCAvp0eya8eui_a9QJ-kfmYMxVwg_cbo/edit?usp=sharing
- **Trello Board:** https://trello.com/b/Zjr8Rj9g

## Team

| Member | Part |
| --- | --- |
| Devis | Dataset integration, cleaning, derived features, exclusion log and final data verification |
| Ivan | Database design, loading scripts and project documentation |
| Samuel | Frontend dashboard |

## 1. Project overview

New York publishes every yellow taxi trip. We use three official TLC components together:

| Component | File | Join key |
| --- | --- | --- |
| Trip records (fact table) | `data/raw/yellow_tripdata_2019-01.csv` | `PULocationID` and `DOLocationID` |
| Zone lookup (dimension table) | `data/raw/taxi_zone_lookup.csv` | `LocationID` |
| Zone shapes (spatial metadata) | `data/raw/taxi_zones.zip` | `LocationID` |

The January 2019 file has 7,667,792 trips. After cleaning, 7,555,482 remain (112,310 rows, 1.46%, were removed and every removal is logged with its reason).

How the parts fit together:

```
trip csv + zone lookup + zone shapes
        |
        v
pipeline/   join, clean, normalize, add features
        |
        v
data/processed/trips_clean.parquet
        |
        v
database/load_db.py  ->  MySQL
        |
        v
backend/  Flask API  ->  frontend/  dashboard
```

## 2. Tech stack

| Layer | Choice |
| --- | --- |
| Data pipeline | Python, pandas, pyarrow, pyshp, pyproj |
| Backend | Flask (Python) |
| Database | MySQL |
| Frontend | HTML, CSS, JavaScript |

## 3. Prerequisites

- Git
- Python 3.10 or newer (developed on Python 3.12)
- MySQL 8.0.16 or newer (the schema uses CHECK constraints)
- The course trip file `yellow_tripdata_2019-01.csv` (too large for git)
- About 8 GB of RAM. The cleaning works in chunks of 500,000 rows, so it also ran in WSL with 7.6 GB.

Notes for Windows with WSL (Ubuntu):
- Use the Linux commands in this README inside the WSL terminal.
- Ubuntu blocks `pip install` outside a virtual environment (the "externally-managed-environment" error), so always create and activate the venv first. If `python3 -m venv` fails, run `sudo apt install python3-venv python3-full`.

## 4. Setup

### 4.0 Python environment

From the project root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows without WSL, activate with `venv\Scripts\activate` instead. The prompt shows `(venv)` when it is active. Activate it again every time you open a new terminal.

### 4.1 Data files

`taxi_zone_lookup.csv` and `taxi_zones.zip` are already in `data/raw/`. Copy the course trip file into the same folder and keep the name `yellow_tripdata_2019-01.csv`. Do not open it in Excel and save it again, because that can change the dates. The file is not committed to git.

Run the pipeline from the project root:

```bash
python pipeline/clean_data.py
python pipeline/validate_clean.py
python pipeline/export_geojson.py
```

- `clean_data.py` joins the three sources, removes invalid rows, fixes and normalizes values, adds the derived features and writes the outputs. It takes several minutes on the full file. Add `--max-rows 200000` for a quick test run.
- `validate_clean.py` checks the cleaned file against every rule. It must end with `PASSED`.
- `export_geojson.py` converts the zone shapefile to GeoJSON for the map.

For the January 2019 file the run reports 7,667,792 rows read and 7,555,482 kept.

Outputs:

| File | Content |
| --- | --- |
| `data/processed/trips_clean.parquet` | cleaned trips: the cleaned columns, the zone details for pickup and dropoff and 8 derived features (not committed, too large) |
| `data/processed/zones.csv`, `vendors.csv`, `rate_codes.csv`, `payment_types.csv` | reference tables for the database |
| `data/processed/zones.geojson` | zone polygons for the map |
| `logs/cleaning_report.txt` | rows before and after, removals by rule, fixes, key numbers before and after |
| `logs/exclusion_summary.csv` | count for every rule |
| `logs/excluded_records.csv` | up to 500 example rows for every rule |
| `logs/before_after_summary.csv` | key numbers before and after cleaning |
| `logs/quality_report.txt` | problems found before cleaning |
| `logs/validation_report.txt` | result of the final check |

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

They check every cleaning rule, the derived features and the route algorithm with hand-made examples.

More detail: `pipeline/README.md`, `pipeline/FIELDS.md` (every column), `pipeline/CLEANING_RULES.md` (every rule with its limit and reason) and `pipeline/FEATURES.md` (the derived features and why they are useful).

### 4.2 Database (MySQL 8.0.16 or newer)

1. Start MySQL (on WSL/Ubuntu: `sudo service mysql start`).
2. Create the database and user:
```sql
   CREATE DATABASE urban_mobility CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'mobility_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON urban_mobility.* TO 'mobility_user'@'localhost';
   FLUSH PRIVILEGES;
```
3. Copy `.env.example` to `.env` and set `DB_PASSWORD`.
4. Make sure `data/processed/trips_clean.parquet` exists (created by `python pipeline/clean_data.py`).
5. Create the tables and load the data (about 10 minutes). To test quickly first, add `--limit 100000`:
```bash
   python database/load_db.py
```
6. Check the result: `source database/test_queries.sql;` inside the `mysql` client.

Schema files: `database/schema.sql` (tables), `database/indexes.sql` (indexes), `database/schema_dump.sql` (structure dump)

#### Verify, rebuild and tune the database

- `python database/verify_db.py` checks tables, keys, indexes, constraints and data (expect "37 checks passed, 0 failed").
- To compare MySQL with the cleaned parquet (row counts, invalid values, zone mapping, nulls, distributions), run `python verification/verify_mysql.py --database urban_mobility --user mobility_user --zone-name-column zone_name`. It asks for the password and saves `logs/database_verification.txt`. See `verification/README.md`.
- No cleaned parquet? Restore the small sample: create an empty database, then
  `mysql -u <user> -p <database> < database/schema_dump.sql` and `mysql -u <user> -p <database> < database/sample_data.sql`
  (all lookup tables plus 1,000 trips).
- Recommended for the full 7.5 million trips: `innodb_buffer_pool_size = 2G` in `/etc/mysql/mysql.conf.d/mysqld.cnf`
  (under `[mysqld]`), then `sudo service mysql restart`.
- `python backend/benchmark_api.py` times every API endpoint.

### 4.3 Backend
Start MySQL, make sure the data is loaded, then from the project root:
```bash
python backend/app.py        # http://127.0.0.1:5000
python backend/test_api.py   # runs the 18 API tests
```

All endpoints are GET and return JSON. Errors look like `{"error": "message"}` (400 bad input, 404 not found, 503 database problem).

| Endpoint | Returns |
|---|---|
| `/api/health` | API and database status |
| `/api/filters` | Date range, max distance/fare, boroughs, payment types (to build filter controls) |
| `/api/summary` | KPIs: total trips, revenue, average fare, distance, duration, tip, speed |
| `/api/trips` | A page of trips (`sort_by`, `order`, `page`, `per_page`) |
| `/api/trips/<id>` | One trip with all details |
| `/api/zones` | All 265 zones with borough and map centre |
| `/api/zones/<id>` | Zone profile: pickups, dropoffs, top 5 destinations |
| `/api/charts/hourly` | Trips and average fare per hour (24 entries) |
| `/api/charts/daily` | Trips and revenue per day |
| `/api/charts/boroughs` | Trips per pickup borough |
| `/api/charts/top-zones` | Busiest zones (`by=pickup\|dropoff`, `limit`) |
| `/api/charts/payment-types` | Trips per payment type |
| `/api/charts/distance-distribution` | Trips per distance range |

**Filters** (work on `/api/summary`, `/api/trips`, `/api/zones/<id>` and all `/api/charts/*`):
`start_date`, `end_date` (YYYY-MM-DD, end day included), `pickup_zone_id`, `dropoff_zone_id` (1-265),
`pickup_borough` (name), `min_distance`, `max_distance` (miles, 0-100),
`min_fare`, `max_fare` (total amount paid, 0-1000), `payment_type_id`.

**Trips only:** `sort_by` (`pickup_datetime`, `trip_distance`, `total_amount`), `order` (`asc`, `desc`),
`page` (1-10000), `per_page` (1-100).

### 4.4 Frontend

Flask serves the frontend and API together. From the project root with the Python environment active:

```bash
python backend/app.py
```

Open http://127.0.0.1:5000 in your browser. The dashboard uses the API on the same address; check API and database connectivity at http://127.0.0.1:5000/api/health. **No separate frontend dev server is required.**

## 5. Running the project

### Quick start for graders (sample database)

Use the bundled 1,000-trip sample; the raw trip CSV and full pipeline are only needed for the optional full setup below. Run commands from the project root.

1. Install and start MySQL 8.0.16 or newer. Create the Python environment and install requirements as shown in section 4.0.
2. In the MySQL client as an administrator, create the database and user using the SQL in section 4.2.
3. Copy the configuration and set `DB_PASSWORD` in `.env` to the password you chose:
   ```bash
   cp .env.example .env
   ```
4. Import the schema into the new, empty database:
   ```bash
   mysql -u mobility_user -p urban_mobility < database/schema_dump.sql
   ```
5. Import the sample data:
   ```bash
   mysql -u mobility_user -p urban_mobility < database/sample_data.sql
   ```
6. With the Python environment active, start Flask:
   ```bash
   python backend/app.py
   ```
7. Open http://127.0.0.1:5000. Check http://127.0.0.1:5000/api/health for API/database status.

### Using an existing XAMPP database locally

Start MySQL in XAMPP. For the local `urban_mobility` database, use these settings in your ignored `.env`:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=urban_mobility
```

XAMPP includes MariaDB; the Flask connection supports its query timeout setting as well as MySQL's. No Homebrew MySQL installation is needed. If the database is empty, import the bundled schema and sample once:

```bash
/Applications/XAMPP/xamppfiles/bin/mysql -h 127.0.0.1 -u root urban_mobility < database/schema_dump.sql
/Applications/XAMPP/xamppfiles/bin/mysql -h 127.0.0.1 -u root urban_mobility < database/sample_data.sql
python backend/app.py
```

Open http://127.0.0.1:5000. Restart Flask after changing `.env`.

### Optional full-data setup

On a fresh clone, in this order:

1. Create and activate the Python environment and install the requirements (section 4.0).
2. Copy `yellow_tripdata_2019-01.csv` into `data/raw/` (section 4.1).
3. Clean the data: `python pipeline/clean_data.py`, then `python pipeline/validate_clean.py` and `python pipeline/export_geojson.py` (section 4.1).
4. Start MySQL, create the database and user, copy `.env.example` to `.env`, then load the data with `python database/load_db.py` (section 4.2).
5. Start the backend with `python backend/app.py` (section 4.3).
6. Open the dashboard (section 4.4).

## 6. Project structure

```
data/
  raw/            taxi_zone_lookup.csv, taxi_zones.zip and the trip csv (csv not committed)
  processed/      cleaned parquet, reference tables, zones.geojson
pipeline/         read, join, clean, normalize, derive features, export
backend/          Flask API
database/         schema, indexes, loader, test queries, sample data
frontend/         dashboard (HTML, CSS, JavaScript)
verification/     tools that compare MySQL and the API with the cleaned data
tests/            unit tests for the cleaning rules, features and algorithm
logs/             cleaning, exclusion, validation and verification reports
docs/             schema design, decision log and report drafts
```

## 7. Documentation

- Technical report (PDF): [Urban Mobility Technical Report](Urban_Mobility_Technical_Report.pdf)
- Data pipeline: `pipeline/README.md`, `pipeline/FIELDS.md`, `pipeline/CLEANING_RULES.md`, `pipeline/FEATURES.md`
- Cleaning evidence: `logs/cleaning_report.txt`, `logs/exclusion_summary.csv`, `logs/excluded_records.csv`
- Database: `database/schema.sql`, `database/indexes.sql`, `database/schema_dump.sql`, `docs/schema_design.md`, `docs/decision_log.md`
- Verification: `verification/README.md`, `logs/database_verification.txt`
- Video walkthrough: https://drive.google.com/drive/folders/1dzm_Kt-q5SeBAS5cxXOiqn3UQkaUXOdK?usp=sharing
