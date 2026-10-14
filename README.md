# Urban Mobility Data Explorer

> TODO: 1-2 sentences in our own words on what this project does.

- **Video walkthrough:** TODO
- **Team participation sheet:** TODO
- **Team members:** TODO

## 1. Projecr overview
TODO

## 2. Tech stack
| Layer | Choice |
|---|---|
| Backend | Flask (Python) |
| Database | MySQL |
| Frontend | TODO |

## 3. Prerequisites
TODO (Python version, MySQL version, Git, WSL notes)

## 4. Setup
### 4.1 Data files
TODO
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
TODO

## 5. Running the project
TODO

## 6. Project Structure
TODO

## 7. Documentation
TODO (report, schema, database dump)