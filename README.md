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
TODO
### 4.4 Frontend
TODO

## 5. Running the project
TODO

## 6. Project Structure
TODO

## 7. Documentation
TODO (report, schema, database dump)