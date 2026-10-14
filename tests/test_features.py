import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))

from features import add_features


def make_frame():
    return pd.DataFrame({
        "pickup_datetime": pd.to_datetime([
            "2019-01-10 08:00:00",
            "2019-01-12 02:30:00",
            "2019-01-13 22:15:00",
        ]),
        "duration_min": [20.0, 30.0, 12.0],
        "trip_distance": [3.0, 5.0, 1.5],
        "fare_amount": [14.0, 20.0, 8.0],
        "tip_amount": [2.0, 0.0, 1.0],
        "payment_type_id": [1, 2, 1],
    })


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.result = add_features(make_frame())

    def test_average_speed(self):
        self.assertEqual(self.result["avg_speed_mph"].tolist(), [9.0, 10.0, 7.5])

    def test_fare_per_mile(self):
        self.assertEqual(self.result["fare_per_mile"].tolist(), [4.67, 4.0, 5.33])

    def test_tip_percent_only_for_card(self):
        tips = self.result["tip_pct"].tolist()
        self.assertEqual(tips[0], 14.29)
        self.assertTrue(pd.isna(tips[1]))
        self.assertEqual(tips[2], 12.5)

    def test_time_parts(self):
        self.assertEqual(self.result["pickup_hour"].tolist(), [8, 2, 22])
        self.assertEqual(self.result["pickup_dow"].tolist(), [3, 5, 6])
        self.assertEqual(self.result["pickup_date"].tolist(), ["2019-01-10", "2019-01-12", "2019-01-13"])

    def test_weekend_flag(self):
        self.assertEqual(self.result["is_weekend"].tolist(), [0, 1, 1])

    def test_time_period(self):
        self.assertEqual(self.result["time_period"].tolist(), ["morning", "night", "late_night"])


if __name__ == "__main__":
    unittest.main()
