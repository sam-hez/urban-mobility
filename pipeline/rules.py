import numpy as np
import pandas as pd

MIN_DURATION = 1
MAX_DURATION = 180
MAX_DISTANCE = 100
MAX_FARE = 500
MAX_TOTAL = 1000
MAX_TIP = 500
MAX_PASSENGERS = 6
MAX_SPEED = 80

CRITICAL = [
    "pickup_datetime", "dropoff_datetime", "pickup_location_id", "dropoff_location_id",
    "trip_distance", "fare_amount", "tip_amount", "tolls_amount", "total_amount",
]

DUPLICATE_COLUMNS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "pickup_location_id",
    "dropoff_location_id", "trip_distance", "fare_amount", "total_amount",
]

NUMBER_COLUMNS = [
    "vendor_id", "passenger_count", "trip_distance", "rate_code_id", "pickup_location_id",
    "dropoff_location_id", "payment_type_id", "fare_amount", "tip_amount", "tolls_amount", "total_amount",
]


def prepare(df):
    df = df.copy()
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"], errors="coerce")
    df["dropoff_datetime"] = pd.to_datetime(df["dropoff_datetime"], errors="coerce")
    for column in NUMBER_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["duration_min"] = (df["dropoff_datetime"] - df["pickup_datetime"]).dt.total_seconds() / 60
    return df


def make_context(df, zone_ids):
    periods = df["pickup_datetime"].dt.to_period("M")
    return {"zone_ids": set(zone_ids), "main_period": periods.mode()[0]}


def make_chunk_context(zone_ids, main_period):
    return {
        "zone_ids": set(zone_ids),
        "main_period": main_period,
        "seen_hashes": np.array([], dtype=np.uint64),
    }


def missing_critical(df, context):
    return df[CRITICAL].isna().any(axis=1)


def duplicate(df, context):
    flagged = df.duplicated(subset=DUPLICATE_COLUMNS)
    seen = context.get("seen_hashes")
    if seen is None:
        return flagged
    hashes = pd.util.hash_pandas_object(df[DUPLICATE_COLUMNS], index=False).to_numpy()
    flagged = flagged | pd.Series(np.isin(hashes, seen), index=df.index)
    context["seen_hashes"] = np.concatenate([seen, hashes[~flagged.to_numpy()]])
    return flagged


def dropoff_not_after_pickup(df, context):
    return df["dropoff_datetime"] <= df["pickup_datetime"]


def outside_month(df, context):
    return df["pickup_datetime"].dt.to_period("M") != context["main_period"]


def duration_too_short(df, context):
    return df["duration_min"] < MIN_DURATION


def duration_too_long(df, context):
    return df["duration_min"] > MAX_DURATION


def distance_not_positive(df, context):
    return df["trip_distance"] <= 0


def distance_too_long(df, context):
    return df["trip_distance"] > MAX_DISTANCE


def fare_out_of_range(df, context):
    return (df["fare_amount"] <= 0) | (df["fare_amount"] > MAX_FARE)


def total_out_of_range(df, context):
    return (df["total_amount"] <= 0) | (df["total_amount"] > MAX_TOTAL)


def negative_extras(df, context):
    return (df["tip_amount"] < 0) | (df["tolls_amount"] < 0)


def tip_out_of_range(df, context):
    return df["tip_amount"] > MAX_TIP


def total_below_fare(df, context):
    return df["total_amount"] < df["fare_amount"]


def unknown_zone(df, context):
    zone_ids = context["zone_ids"]
    return ~(df["pickup_location_id"].isin(zone_ids) & df["dropoff_location_id"].isin(zone_ids))


def passenger_count_invalid(df, context):
    return (df["passenger_count"] < 0) | (df["passenger_count"] > MAX_PASSENGERS)


def speed_impossible(df, context):
    hours = df["duration_min"] / 60
    return (hours > 0) & ((df["trip_distance"] / hours) > MAX_SPEED)


RULES = [
    ("missing_critical", "Missing time, zone, distance or money value", missing_critical),
    ("duplicate", "Same vendor, times, zones, distance and fare as an earlier row", duplicate),
    ("dropoff_not_after_pickup", "Dropoff time is not after pickup time", dropoff_not_after_pickup),
    ("outside_month", "Pickup is outside the month the file belongs to", outside_month),
    ("duration_too_short", "Trip shorter than {} minute".format(MIN_DURATION), duration_too_short),
    ("duration_too_long", "Trip longer than {} minutes".format(MAX_DURATION), duration_too_long),
    ("distance_not_positive", "Trip distance is zero or negative", distance_not_positive),
    ("distance_too_long", "Trip distance above {} miles".format(MAX_DISTANCE), distance_too_long),
    ("fare_out_of_range", "Fare is zero, negative or above {} dollars".format(MAX_FARE), fare_out_of_range),
    ("total_out_of_range", "Total is zero, negative or above {} dollars".format(MAX_TOTAL), total_out_of_range),
    ("negative_extras", "Negative tip or toll amount", negative_extras),
    ("tip_out_of_range", "Tip above {} dollars".format(MAX_TIP), tip_out_of_range),
    ("total_below_fare", "Total amount is lower than the metered fare", total_below_fare),
    ("unknown_zone", "Zone id is not in taxi_zone_lookup.csv", unknown_zone),
    ("passenger_count_invalid", "Negative or more than {} passengers".format(MAX_PASSENGERS), passenger_count_invalid),
    ("speed_impossible", "Average speed above {} mph".format(MAX_SPEED), speed_impossible),
]
