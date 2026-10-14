# Derived features

Made in `pipeline/features.py` and added to every cleaned trip by `clean_data.py`.

| Feature | Formula | Why it is useful |
| --- | --- | --- |
| avg_speed_mph | trip_distance / (duration_min / 60) | Shows congestion. Speed falls at rush hour and on busy routes, so it measures how well the city moves, not only how many trips happen. |
| fare_per_mile | fare_amount / trip_distance | Compares the cost of short and long trips. Short trips are expensive per mile because of the starting charge, airport and bridge trips are cheaper per mile. |
| tip_pct | tip_amount / fare_amount * 100, card payments only | Shows how generous riders are. Cash tips are not recorded in the data, so cash trips are left empty and not counted as 0%. |
| pickup_date | date part of pickup time | Lets the database and the dashboard group trips by day without parsing times. |
| pickup_hour | hour part of pickup time, 0 to 23 | Shows the daily rhythm of the city. |
| pickup_dow | weekday of pickup, 0 is Monday and 6 is Sunday | Compares weekdays with weekends. |
| is_weekend | 1 if pickup_dow is 5 or 6 | A simple filter for commuter and leisure patterns. |
| time_period | night 0-5, morning 6-10, midday 11-15, evening 16-20, late_night 21-23 | Groups hours into parts of the day for easier charts. |

The first three are calculated from several raw columns and give new information about movement and money. The other five come from the pickup time and make grouping and filtering simpler.

## Notes for the report

- All inputs are already cleaned, so duration is at least 1 minute and distance is above 0. No division by zero is possible.
- fare_per_mile has no upper limit. Very short trips with the starting charge can give high values, and these are real trips.
- tip_pct is empty for every trip that was not paid by card.
- `python3 -m unittest discover -s tests` checks the formulas with hand-made examples.
