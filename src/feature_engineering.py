"""
feature_engineering.py
-----------------------
Stage 2 of the FleetIQ pipeline: turn the cleaned zone x hour demand table
into a model-ready feature matrix.

Adds:
  - calendar features: hour, day-of-week, month, weekend flag, holiday flag
  - cyclical encodings of hour / day-of-week (sin/cos)
  - historical-demand features: previous-hour demand, previous-day
    same-hour demand, 3h/24h/7d rolling averages
  - a simple weather-proxy feature (rain flag), used the same way real
    weather data would be joined in if available

Input : data/processed/zone_hour_demand.parquet
Output: data/processed/model_features.parquet
"""
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PROC_DIR = BASE / "data" / "processed"

HOLIDAYS_2024 = pd.to_datetime([
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-31",
])


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ts = df["pickup_hour"]
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek  # 0=Mon
    df["day_of_month"] = ts.dt.day
    df["month"] = ts.dt.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_holiday"] = ts.dt.normalize().isin(HOLIDAYS_2024).astype(int)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    # weather proxy, consistent with the generator's synthetic "rain days"
    df["is_rainy"] = (ts.dt.dayofyear % 11 == 0).astype(int)
    return df


def add_lag_and_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["zone_id", "pickup_hour"]).copy()
    g = df.groupby("zone_id")["demand"]

    df["lag_1h"] = g.shift(1)
    df["lag_24h"] = g.shift(24)
    df["lag_168h"] = g.shift(168)  # same hour, previous week

    df["roll_mean_3h"] = g.shift(1).rolling(3).mean().reset_index(level=0, drop=True)
    df["roll_mean_24h"] = g.shift(1).rolling(24).mean().reset_index(level=0, drop=True)
    df["roll_mean_168h"] = g.shift(1).rolling(168).mean().reset_index(level=0, drop=True)
    df["roll_std_24h"] = g.shift(1).rolling(24).std().reset_index(level=0, drop=True)

    lag_cols = ["lag_1h", "lag_24h", "lag_168h", "roll_mean_3h", "roll_mean_24h",
                "roll_mean_168h", "roll_std_24h"]
    for c in lag_cols:
        df[c] = df[c].fillna(df.groupby("zone_id")["demand"].transform("mean"))

    return df


def encode_zone(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["zone_avg_demand"] = df.groupby("zone_id")["demand"].transform("mean")
    df["borough_code"] = df["Borough"].astype("category").cat.codes
    return df


def main():
    print("Loading processed zone-hour demand...")
    df = pd.read_parquet(PROC_DIR / "zone_hour_demand.parquet")

    df = add_calendar_features(df)
    df = add_lag_and_rolling_features(df)
    df = encode_zone(df)

    out_path = PROC_DIR / "model_features.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df):,} rows x {df.shape[1]} columns -> {out_path}")
    print("Feature columns:", [c for c in df.columns if c not in
          ("zone_id", "pickup_hour", "Zone", "Borough")])


if __name__ == "__main__":
    main()
