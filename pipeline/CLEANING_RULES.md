# Cleaning and normalization rules

All limits are at the top of `pipeline/rules.py`. A row is removed under the first rule it fails, and every removal is counted in `logs/exclusion_summary.csv`.

## Rows removed

| Rule | Group | Limit | Why |
| --- | --- | --- | --- |
| missing_critical | missing values | any empty time, zone, distance or money value | the trip cannot be analysed without them |
| duplicate | duplicates | same vendor, times, zones, distance and fare as an earlier row | counted twice would inflate trip counts |
| dropoff_not_after_pickup | timestamps | dropoff <= pickup | time cannot run backwards |
| outside_month | timestamps | pickup not in the main month of the file | stray dates such as 2008 or the previous year are meter errors |
| duration_too_short | timestamps | under 1 minute | cancelled or test trips |
| duration_too_long | timestamps | over 180 minutes | meter left running |
| distance_not_positive | distance | 0 or negative | no movement, but a fare was charged |
| distance_too_long | distance | over 100 miles | not possible for a taxi inside the city area |
| speed_impossible | impossible records | over 80 mph | distance and time do not fit together |
| fare_out_of_range | fare | 0, negative or over 500 dollars | refunds, test entries and typos |
| total_out_of_range | fare | 0, negative or over 1000 dollars | same as above |
| negative_extras | fare | negative tip or tolls | not valid charges |
| tip_out_of_range | fare | tip over 500 dollars | a tip larger than the highest allowed fare is a data entry error |
| total_below_fare | impossible records | total amount lower than fare amount | the total includes the fare, so it cannot be smaller |
| unknown_zone | impossible records | zone id not in taxi_zone_lookup.csv | the trip could not be placed on the map |
| passenger_count_invalid | impossible records | negative or over 6 passengers | not possible for a yellow taxi |

## Values fixed in rows that are kept

| Field | Fix |
| --- | --- |
| passenger_count | empty or 0 becomes 1 |
| vendor_id | empty or not in the reference list becomes 0 (unknown) |
| rate_code_id | empty or not in the reference list becomes 99 (unknown) |
| payment_type_id | empty or not in the reference list becomes 5 (unknown) |
| store_and_fwd_flag | trimmed and upper-cased, anything other than Y or N becomes empty |
| extra, mta_tax, improvement_surcharge, congestion_surcharge, airport_fee | empty becomes 0.0, the fee was not charged or did not exist yet in that year |

## Normalization

| What | Standard |
| --- | --- |
| Timestamps | real datetime values with no time zone, parsed from text, US-style dates are accepted |
| Whole-number fields | 64-bit integers (ids, passenger count) |
| Money, distance, duration | 64-bit decimals rounded to 2 places |
| Categorical ids | checked against `reference.py`, saved as `vendors.csv`, `rate_codes.csv`, `payment_types.csv` and `zones.csv` |

## Left empty on purpose

`pickup_lat`, `pickup_lon`, `dropoff_lat` and `dropoff_lon` stay empty for zones without a polygon (57, 104, 105, 264 and 265). Inventing a position would be wrong.
