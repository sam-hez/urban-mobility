import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))

from rules import RULES, make_chunk_context, prepare

RULE_FUNCTIONS = {name: function for name, _, function in RULES}


def good_row(**changes):
    row = {
        "vendor_id": 1,
        "pickup_datetime": "2019-01-10 08:00:00",
        "dropoff_datetime": "2019-01-10 08:20:00",
        "passenger_count": 1,
        "trip_distance": 3.0,
        "rate_code_id": 1,
        "pickup_location_id": 161,
        "dropoff_location_id": 236,
        "payment_type_id": 1,
        "fare_amount": 14.0,
        "tip_amount": 2.0,
        "tolls_amount": 0.0,
        "total_amount": 18.0,
    }
    row.update(changes)
    return row


def run_rule(name, rows):
    df = prepare(pd.DataFrame(rows))
    context = make_chunk_context(range(1, 266), pd.Period("2019-01", "M"))
    return RULE_FUNCTIONS[name](df, context).tolist()


BAD_CASES = {
    "missing_critical": {"fare_amount": None},
    "dropoff_not_after_pickup": {"dropoff_datetime": "2019-01-10 08:00:00"},
    "outside_month": {"pickup_datetime": "2018-12-31 23:00:00", "dropoff_datetime": "2018-12-31 23:20:00"},
    "duration_too_short": {"dropoff_datetime": "2019-01-10 08:00:30"},
    "duration_too_long": {"dropoff_datetime": "2019-01-10 12:30:00"},
    "distance_not_positive": {"trip_distance": 0.0},
    "distance_too_long": {"trip_distance": 150.0},
    "fare_out_of_range": {"fare_amount": -5.0},
    "total_out_of_range": {"total_amount": 2000.0},
    "negative_extras": {"tip_amount": -1.0},
    "tip_out_of_range": {"tip_amount": 600.0},
    "total_below_fare": {"total_amount": 10.0},
    "unknown_zone": {"pickup_location_id": 999},
    "passenger_count_invalid": {"passenger_count": 9},
    "speed_impossible": {"trip_distance": 60.0},
}


class RuleTests(unittest.TestCase):
    def test_every_rule_has_a_test_case(self):
        tested = set(BAD_CASES) | {"duplicate"}
        self.assertEqual(tested, set(RULE_FUNCTIONS))

    def test_bad_rows_are_flagged_and_good_rows_are_not(self):
        for name, changes in BAD_CASES.items():
            with self.subTest(rule=name):
                flags = run_rule(name, [good_row(), good_row(**changes)])
                self.assertEqual(flags, [False, True])

    def test_fare_above_limit_is_flagged(self):
        flags = run_rule("fare_out_of_range", [good_row(), good_row(fare_amount=600.0)])
        self.assertEqual(flags, [False, True])

    def test_duplicate_flags_only_the_second_copy(self):
        flags = run_rule("duplicate", [good_row(), good_row(), good_row(fare_amount=15.0)])
        self.assertEqual(flags, [False, True, False])

    def test_duplicates_across_chunks(self):
        context = make_chunk_context(range(1, 266), pd.Period("2019-01", "M"))
        first = prepare(pd.DataFrame([good_row()]))
        second = prepare(pd.DataFrame([good_row()]))
        self.assertEqual(RULE_FUNCTIONS["duplicate"](first, context).tolist(), [False])
        self.assertEqual(RULE_FUNCTIONS["duplicate"](second, context).tolist(), [True])

    def test_a_good_row_passes_every_rule(self):
        for name in RULE_FUNCTIONS:
            with self.subTest(rule=name):
                self.assertEqual(run_rule(name, [good_row()]), [False])


if __name__ == "__main__":
    unittest.main()
