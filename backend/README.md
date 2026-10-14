# Backend

Flask API for the dashboard. This is the first version: the structure, a health check and the endpoints that do not need the database.

## Run

```
pip install -r requirements.txt
python backend/app.py
```

The server starts at http://127.0.0.1:5000

## Files

| File | Purpose |
| --- | --- |
| app.py | creates the Flask app, adds the CORS header and the JSON error pages |
| settings.py | file paths, host and port |
| db.py | opens the SQLite database and runs queries |
| routes/system.py | the endpoints below |
| algorithms.py | hand-written min heap and top-k busiest routes |

## Endpoints now

| Endpoint | Gives |
| --- | --- |
| /api/health | server status and which data files exist |
| /api/zones.geojson | zone polygons for the map (run `python pipeline/export_geojson.py` first) |
| /api/cleaning | cleaning summary from `logs/exclusion_summary.csv` (run `python pipeline/clean_data.py` first) |

New endpoints go in a new file inside `routes/` and are registered in `app.py` with `app.register_blueprint(...)`.

## Algorithm

`algorithms.py` finds the busiest routes without `Counter`, `heapq` or any sort function. It counts each (pickup, dropoff) pair in a dictionary and keeps the best k in a min heap written by hand. Time is O(n + m log k) and space is O(m), where n is the number of trips, m the number of different routes and k the number of results.
