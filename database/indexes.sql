CREATE INDEX idx_trips_pickup_dt ON trips (pickup_datetime);
CREATE INDEX idx_trips_pu_dt ON trips (pickup_location_id, pickup_datetime);
CREATE INDEX idx_trips_distance ON trips (trip_distance);                        
CREATE INDEX idx_trips_total ON trips (total_amount);