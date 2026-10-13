CREATE TABLE IF NOT EXISTS boroughs (
    borough_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    borough_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (borough_id),
    UNIQUE KEY uq_borough_name (borough_name)
);

CREATE TABLE IF NOT EXISTS service_zones (
    service_zone_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    service_zone_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (service_zone_id),
    UNIQUE KEY uq_service_zone_name (service_zone_name)
);

CREATE TABLE IF NOT EXISTS vendors (
    vendor_id TINYINT UNSIGNED NOT NULL,
    vendor_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (vendor_id)
);

CREATE TABLE IF NOT EXISTS rate_codes (
    rate_code_id TINYINT UNSIGNED NOT NULL,
    description VARCHAR(100) NOT NULL,
    PRIMARY KEY (rate_code_id)
);

CREATE TABLE IF NOT EXISTS payment_types (
    payment_type_id TINYINT UNSIGNED NOT NULL,
    description VARCHAR(100) NOT NULL,
    PRIMARY KEY (payment_type_id)
);

CREATE TABLE IF NOT EXISTS zones (
    location_id SMALLINT UNSIGNED NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    borough_id TINYINT UNSIGNED NOT NULL,
    service_zone_id TINYINT UNSIGNED NOT NULL,
    polygon_parts TINYINT UNSIGNED NULL,
    centroid_lat DECIMAL(9,6) NULL,
    centroid_lon DECIMAL(9,6) NULL,
    PRIMARY KEY (location_id),
    CONSTRAINT fk_zones_borough
        FOREIGN KEY (borough_id) REFERENCES boroughs (borough_id),
    CONSTRAINT fk_zones_service_zone
        FOREIGN KEY (service_zone_id) REFERENCES service_zones (service_zone_id)
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    vendor_id TINYINT UNSIGNED NOT NULL,
    pickup_datetime DATETIME NOT NULL,
    dropoff_datetime DATETIME NOT NULL,
    pickup_location_id SMALLINT UNSIGNED NOT NULL,
    dropoff_location_id SMALLINT UNSIGNED NOT NULL,
    rate_code_id TINYINT UNSIGNED NOT NULL,
    payment_type_id TINYINT UNSIGNED NOT NULL,
    passenger_count TINYINT UNSIGNED NOT NULL,
    trip_distance DECIMAL(8,2) NOT NULL,
    store_and_fwd_flag CHAR(1) NULL,

    fare_amount DECIMAL(8,2) NOT NULL,
    extra DECIMAL(8,2) NOT NULL DEFAULT 0,
    mta_tax DECIMAL(8,2) NOT NULL DEFAULT 0,
    tip_amount DECIMAL(8,2) NOT NULL,
    tolls_amount DECIMAL(8,2) NOT NULL,
    improvement_surcharge DECIMAL(8,2) NOT NULL DEFAULT 0,
    congestion_surcharge DECIMAL(8,2) NOT NULL DEFAULT 0,
    airport_fee DECIMAL(8,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(8,2) NOT NULL,

    duration_min DECIMAL(8,2) NOT NULL,

    PRIMARY KEY (trip_id),
    CONSTRAINT fk_trips_vendor FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id),
    CONSTRAINT fk_trips_pickup FOREIGN KEY (pickup_location_id) REFERENCES zones (location_id),
    CONSTRAINT fk_trips_dropoff FOREIGN KEY (dropoff_location_id) REFERENCES zones (location_id),
    CONSTRAINT fk_trips_rate FOREIGN KEY (rate_code_id) REFERENCES rate_codes (rate_code_id),
    CONSTRAINT fk_trips_payment FOREIGN KEY (payment_type_id) REFERENCES payment_types (payment_type_id),

    CONSTRAINT chk_times CHECK (dropoff_datetime > pickup_datetime),
    CONSTRAINT chk_distance CHECK (trip_distance > 0 AND trip_distance <= 100),
    CONSTRAINT chk_fare CHECK (fare_amount > 0 AND fare_amount <= 500),
    CONSTRAINT chk_total CHECK (total_amount > 0 AND total_amount <= 1000 AND total_amount >= fare_amount),
    CONSTRAINT chk_tip_tolls CHECK (tip_amount >= 0 AND tip_amount <= 500 AND tolls_amount >= 0),
    CONSTRAINT chk_passengers CHECK (passenger_count BETWEEN 1 AND 6),
    CONSTRAINT chk_duration CHECK (duration_min BETWEEN 1 AND 180),
    CONSTRAINT chk_flag CHECK (store_and_fwd_flag IN ('Y', 'N') OR store_and_fwd_flag IS NULL)
);