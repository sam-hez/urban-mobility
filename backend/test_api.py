import unittest

from app import app


class ApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        options = cls.client.get("/api/filters").get_json()
        cls.first_day = options["min_date"][:10]
        cls.last_day = options["max_date"][:10]

    def get(self, url, expected_status=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status, f"{url} -> {response.get_json()}")
        return response.get_json()

    def test_health(self):
        data = self.get("/api/health")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "connected")

    def test_filter_options(self):
        data = self.get("/api/filters")
        for key in ["min_date", "max_date", "max_distance", "max_fare", "boroughs", "payment_types"]:
            self.assertIn(key, data)

    def test_summary(self):
        data = self.get("/api/summary")
        self.assertGreater(data["total_trips"], 0)
        self.assertIn("avg_fare", data)

    def test_summary_filters(self):
        everything = self.get("/api/summary")["total_trips"]
        long_trips = self.get("/api/summary?min_distance=5")["total_trips"]
        self.assertTrue(0 < long_trips < everything)
        one_day = self.get(f"/api/summary?start_date={self.first_day}&end_date={self.first_day}")["total_trips"]
        self.assertTrue(0 < one_day <= everything)
        self.assertEqual(self.get("/api/summary?start_date=2030-01-01")["total_trips"], 0)

    def test_trips_default_page(self):
        data = self.get("/api/trips")
        self.assertEqual(data["page"], 1)
        self.assertEqual(len(data["trips"]), 25)
        self.assertGreater(data["total"], 25)

    def test_trips_per_page(self):
        self.assertEqual(len(self.get("/api/trips?per_page=5")["trips"]), 5)

    def test_trips_sorted_by_distance_descending(self):
        distances = [t["trip_distance"] for t in self.get("/api/trips?sort_by=trip_distance&order=desc&per_page=20")["trips"]]
        self.assertEqual(distances, sorted(distances, reverse=True))

    def test_trips_distance_filter(self):
        trips = self.get("/api/trips?min_distance=10&max_distance=15&per_page=20")["trips"]
        self.assertTrue(len(trips) > 0)
        for trip in trips:
            self.assertTrue(10 <= trip["trip_distance"] <= 15)

    def test_trips_zone_and_borough_filter(self):
        for trip in self.get("/api/trips?pickup_zone_id=161&per_page=10")["trips"]:
            self.assertEqual(trip["pickup_location_id"], 161)
        for trip in self.get("/api/trips?pickup_borough=Manhattan&per_page=10")["trips"]:
            self.assertEqual(trip["pickup_borough"], "Manhattan")

    def test_trips_pages_do_not_overlap(self):
        first = {t["trip_id"] for t in self.get("/api/trips?per_page=10&page=1")["trips"]}
        second = {t["trip_id"] for t in self.get("/api/trips?per_page=10&page=2")["trips"]}
        self.assertEqual(first & second, set())

    def test_trip_detail(self):
        trip_id = self.get("/api/trips?per_page=1")["trips"][0]["trip_id"]
        data = self.get(f"/api/trips/{trip_id}")
        self.assertEqual(data["trip_id"], trip_id)
        self.assertIn("pickup_zone", data)

    def test_zones_list(self):
        self.assertEqual(len(self.get("/api/zones")), 265)

    def test_zone_detail(self):
        data = self.get("/api/zones/161")
        self.assertEqual(data["zone"]["location_id"], 161)
        self.assertIn("top_destinations", data)

    def test_chart_hourly_has_24_hours(self):
        data = self.get("/api/charts/hourly")
        self.assertEqual([row["hour"] for row in data], list(range(24)))

    def test_other_charts(self):
        for url in ["/api/charts/daily", "/api/charts/boroughs", "/api/charts/payment-types",
                    "/api/charts/distance-distribution", "/api/charts/top-zones?limit=5"]:
            self.assertTrue(len(self.get(url)) > 0, url)
        self.assertEqual(len(self.get("/api/charts/top-zones?by=dropoff&limit=3")), 3)

    def test_bad_input_is_rejected(self):
        bad_requests = [
            ("/api/trips?start_date=01-02-2019", 400),
            ("/api/trips?start_date=2019-01-05&end_date=2019-01-01", 400),
            ("/api/trips?per_page=0", 400),
            ("/api/trips?per_page=1000", 400),
            ("/api/trips?page=abc", 400),
            ("/api/trips?sort_by=password", 400),
            ("/api/trips?order=sideways", 400),
            ("/api/trips?min_distance=-5", 400),
            ("/api/trips?min_distance=20&max_distance=10", 400),
            ("/api/trips?pickup_zone_id=999", 400),
            ("/api/trips?pickup_borough=Atlantis", 400),
            ("/api/trips?sort_by=trip_distance;DROP TABLE trips", 400),
            ("/api/charts/top-zones?limit=500", 400),
            ("/api/charts/top-zones?by=moon", 400),
        ]
        for url, status in bad_requests:
            data = self.get(url, expected_status=status)
            self.assertIn("error", data)

    def test_not_found(self):
        self.assertIn("error", self.get("/api/zones/9999", expected_status=404))
        self.assertIn("error", self.get("/api/trips/999999999", expected_status=404))
        self.assertIn("error", self.get("/api/nothing-here", expected_status=404))

    def test_wrong_method(self):
        self.assertEqual(self.client.post("/api/summary").status_code, 405)


if __name__ == "__main__":
    unittest.main(verbosity=2)