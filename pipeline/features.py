import numpy as np
import pandas as pd

TIME_BINS = [-1, 5, 10, 15, 20, 23]
TIME_LABELS = ["night", "morning", "midday", "evening", "late_night"]

FEATURE_COLUMNS = [
    "avg_speed_mph", "fare_per_mile", "tip_pct", "pickup_date",
    "pickup_hour", "pickup_dow", "is_weekend", "time_period",
]


def add_features(df):
    df = df.copy()
    hours = df["duration_min"] / 60
    df["avg_speed_mph"] = (df["trip_distance"] / hours).round(2)
    df["fare_per_mile"] = (df["fare_amount"] / df["trip_distance"]).round(2)
    card = df["payment_type_id"] == 1
    df["tip_pct"] = np.where(card, df["tip_amount"] / df["fare_amount"] * 100, np.nan).round(2)

    pickup = df["pickup_datetime"]
    df["pickup_date"] = pickup.dt.strftime("%Y-%m-%d")
    df["pickup_hour"] = pickup.dt.hour.astype("int64")
    df["pickup_dow"] = pickup.dt.dayofweek.astype("int64")
    df["is_weekend"] = (df["pickup_dow"] >= 5).astype("int64")
    df["time_period"] = pd.cut(df["pickup_hour"], bins=TIME_BINS, labels=TIME_LABELS).astype(str)
    return df
