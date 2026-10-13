SELECT COUNT(*) AS trips_without_pickup_zone
FROM trips t
LEFT JOIN zones z ON z.location_id = t.pickup_location_id
WHERE z.location_id IS NULL;

SELECT COUNT(*) AS trips_without_dropoff_zone
FROM trips t
LEFT JOIN zones z ON z.location_id = t.dropoff_location_id
WHERE z.location_id IS NULL;

SELECT (SELECT COUNT(*) FROM trips) AS trips,
       COUNT(*) AS rows_after_all_joins
FROM trips t
JOIN zones z          ON z.location_id = t.pickup_location_id
JOIN boroughs b       ON b.borough_id = z.borough_id
JOIN service_zones s  ON s.service_zone_id = z.service_zone_id
JOIN vendors v        ON v.vendor_id = t.vendor_id
JOIN rate_codes r     ON r.rate_code_id = t.rate_code_id
JOIN payment_types p  ON p.payment_type_id = t.payment_type_id;

SELECT COUNT(*) AS zones_total,
        SUM(b.borough_id IS NOT NULL AND s.service_zone_id IS NOT NULL) AS zones_fully_joined
FROM zones z
LEFT JOIN boroughs b      ON b.borough_id = z.borough_id
LEFT JOIN service_zones s ON s.service_zone_id = z.service_zone_id;

SELECT HOUR(pickup_datetime) AS hour_of_day,
        COUNT(*) AS trips,
        ROUND(AVG(fare_amount), 2) AS avg_fare
FROM trips
GROUP BY HOUR(pickup_datetime)
ORDER BY hour_of_day;

SELECT b.borough_name, COUNT(*) AS trips
FROM trips t
JOIN zones z    ON z.location_id = t.pickup_location_id
JOIN boroughs b ON b.borough_id = z.borough_id
GROUP BY b.borough_name
ORDER BY trips DESC;

SELECT z.zone_name, b.borough_name, COUNT(*) AS trips
FROM trips t
JOIN zones z    ON z.location_id = t.pickup_location_id
JOIN boroughs b ON b.borough_id = z.borough_id
GROUP BY z.location_id, z.zone_name, b.borough_name
ORDER BY trips DESC
LIMIT 10;

SELECT trip_id, pickup_datetime, trip_distance, total_amount
FROM trips
WHERE pickup_location_id = 161
    AND pickup_datetime >= '2019-01-02' AND pickup_datetime < '2019-01-03'
ORDER BY pickup_datetime
LIMIT 50;

SELECT trip_id, trip_distance, duration_min, total_amount
FROM trips
WHERE trip_distance > 20
ORDER BY trip_distance DESC
LIMIT 20;

SELECT trip_id, total_amount, trip_distance
FROM trips
WHERE total_amount BETWEEN 100 AND 300
ORDER BY total_amount DESC
LIMIT 20;

SELECT p.description AS payment_type, COUNT(*) AS trips,
        ROUND(AVG(t.tip_amount), 2) AS avg_tip
FROM trips t
JOIN payment_types p ON p.payment_type_id = t.payment_type_id
GROUP BY p.payment_type_id, p.description
ORDER BY trips DESC;

SELECT pz.zone_name AS pickup_zone, dz.zone_name AS dropoff_zone, COUNT(*) AS trips
FROM trips t
JOIN zones pz ON pz.location_id = t.pickup_location_id
JOIN zones dz ON dz.location_id = t.dropoff_location_id
GROUP BY t.pickup_location_id, t.dropoff_location_id, pz.zone_name, dz.zone_name
ORDER BY trips DESC
LIMIT 10;

EXPLAIN SELECT trip_id FROM trips
WHERE pickup_location_id = 161
    AND pickup_datetime >= '2019-01-02' AND pickup_datetime < '2019-01-03';

EXPLAIN SELECT trip_id FROM trips WHERE trip_distance > 20 ORDER BY trip_distance DESC LIMIT 20;

EXPLAIN SELECT trip_id FROM trips WHERE total_amount BETWEEN 100 AND 300 ORDER BY total_amount DESC LIMIT 20;