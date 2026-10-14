
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `boroughs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `boroughs` (
  `borough_id` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `borough_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`borough_id`),
  UNIQUE KEY `uq_borough_name` (`borough_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `payment_types`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_types` (
  `payment_type_id` tinyint unsigned NOT NULL,
  `description` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`payment_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `rate_codes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rate_codes` (
  `rate_code_id` tinyint unsigned NOT NULL,
  `description` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`rate_code_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `service_zones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_zones` (
  `service_zone_id` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `service_zone_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`service_zone_id`),
  UNIQUE KEY `uq_service_zone_name` (`service_zone_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `trips`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trips` (
  `trip_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `vendor_id` tinyint unsigned NOT NULL,
  `pickup_datetime` datetime NOT NULL,
  `dropoff_datetime` datetime NOT NULL,
  `pickup_location_id` smallint unsigned NOT NULL,
  `dropoff_location_id` smallint unsigned NOT NULL,
  `rate_code_id` tinyint unsigned NOT NULL,
  `payment_type_id` tinyint unsigned NOT NULL,
  `passenger_count` tinyint unsigned NOT NULL,
  `trip_distance` decimal(8,2) NOT NULL,
  `store_and_fwd_flag` char(1) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fare_amount` decimal(8,2) NOT NULL,
  `extra` decimal(8,2) NOT NULL DEFAULT '0.00',
  `mta_tax` decimal(8,2) NOT NULL DEFAULT '0.00',
  `tip_amount` decimal(8,2) NOT NULL,
  `tolls_amount` decimal(8,2) NOT NULL,
  `improvement_surcharge` decimal(8,2) NOT NULL DEFAULT '0.00',
  `congestion_surcharge` decimal(8,2) NOT NULL DEFAULT '0.00',
  `airport_fee` decimal(8,2) NOT NULL DEFAULT '0.00',
  `total_amount` decimal(8,2) NOT NULL,
  `duration_min` decimal(8,2) NOT NULL,
  PRIMARY KEY (`trip_id`),
  KEY `fk_trips_vendor` (`vendor_id`),
  KEY `fk_trips_dropoff` (`dropoff_location_id`),
  KEY `fk_trips_rate` (`rate_code_id`),
  KEY `fk_trips_payment` (`payment_type_id`),
  KEY `idx_trips_pickup_dt` (`pickup_datetime`),
  KEY `idx_trips_pu_dt` (`pickup_location_id`,`pickup_datetime`),
  KEY `idx_trips_distance` (`trip_distance`),
  KEY `idx_trips_total` (`total_amount`),
  CONSTRAINT `fk_trips_dropoff` FOREIGN KEY (`dropoff_location_id`) REFERENCES `zones` (`location_id`),
  CONSTRAINT `fk_trips_payment` FOREIGN KEY (`payment_type_id`) REFERENCES `payment_types` (`payment_type_id`),
  CONSTRAINT `fk_trips_pickup` FOREIGN KEY (`pickup_location_id`) REFERENCES `zones` (`location_id`),
  CONSTRAINT `fk_trips_rate` FOREIGN KEY (`rate_code_id`) REFERENCES `rate_codes` (`rate_code_id`),
  CONSTRAINT `fk_trips_vendor` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`vendor_id`),
  CONSTRAINT `chk_distance` CHECK (((`trip_distance` > 0) and (`trip_distance` <= 100))),
  CONSTRAINT `chk_duration` CHECK ((`duration_min` between 1 and 180)),
  CONSTRAINT `chk_fare` CHECK (((`fare_amount` > 0) and (`fare_amount` <= 500))),
  CONSTRAINT `chk_flag` CHECK (((`store_and_fwd_flag` in (_utf8mb4'Y',_utf8mb4'N')) or (`store_and_fwd_flag` is null))),
  CONSTRAINT `chk_passengers` CHECK ((`passenger_count` between 1 and 6)),
  CONSTRAINT `chk_times` CHECK ((`dropoff_datetime` > `pickup_datetime`)),
  CONSTRAINT `chk_tip_tolls` CHECK (((`tip_amount` >= 0) and (`tip_amount` <= 500) and (`tolls_amount` >= 0))),
  CONSTRAINT `chk_total` CHECK (((`total_amount` > 0) and (`total_amount` <= 1000) and (`total_amount` >= `fare_amount`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `vendors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vendors` (
  `vendor_id` tinyint unsigned NOT NULL,
  `vendor_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`vendor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `zones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `zones` (
  `location_id` smallint unsigned NOT NULL,
  `zone_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `borough_id` tinyint unsigned NOT NULL,
  `service_zone_id` tinyint unsigned NOT NULL,
  `polygon_parts` tinyint unsigned DEFAULT NULL,
  `centroid_lat` decimal(9,6) DEFAULT NULL,
  `centroid_lon` decimal(9,6) DEFAULT NULL,
  PRIMARY KEY (`location_id`),
  KEY `fk_zones_borough` (`borough_id`),
  KEY `fk_zones_service_zone` (`service_zone_id`),
  CONSTRAINT `fk_zones_borough` FOREIGN KEY (`borough_id`) REFERENCES `boroughs` (`borough_id`),
  CONSTRAINT `fk_zones_service_zone` FOREIGN KEY (`service_zone_id`) REFERENCES `service_zones` (`service_zone_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

