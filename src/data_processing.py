"""
data_processing.py
-------------------
Stage 1 of the FleetIQ pipeline: clean raw TLC-style trip records and
aggregate them into zone x hour demand counts.

Input : data/raw/yellow_tripdata_synthetic_2024.csv (+ taxi_zones.csv)
Output: data/processed/zone_hour_demand.parquet
"""
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "data" / "raw"
PROC_DIR = BASE / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(
        RAW_DIR / "yellow_tripdata_synthetic_2024.csv",
        parse_dates=["tpep_pickup_datetime", "tpep_dropoff_datetime"],
    )
    return df


def clean_trips(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)

    df = df[df["fare_amount"] > 0]
    df = df[(df["trip_distance"] > 0) & (df["trip_distance"] < 100)]
    df = df[df["tpep_dropoff_datetime"] > df["tpep_pickup_datetime"]]

    trip_minutes = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60
    df = df[(trip_minutes > 0.5) & (trip_minutes < 180)]

    df["passenger_count"] = df["passenger_count"].fillna(1).clip(lower=1, upper=6)

    df = df.dropna(subset=["PULocationID", "DOLocationID"])

    n1 = len(df)
    print(f"Cleaned trips: {n0:,} -> {n1:,} rows ({n0 - n1:,} removed, {(n0 - n1) / n0:.1%})")
    return df


def aggregate_zone_hour(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pickup_hour"] = df["tpep_pickup_datetime"].dt.floor("h")

    agg = (
        df.groupby(["PULocationID", "pickup_hour"])
        .agg(
            demand=("trip_id", "count"),
            avg_fare=("fare_amount", "mean"),
            avg_distance=("trip_distance", "mean"),
            avg_passengers=("passenger_count", "mean"),
        )
        .reset_index()
        .rename(columns={"PULocationID": "zone_id"})
    )
    return agg


def fill_zone_hour_grid(agg: pd.DataFrame) -> pd.DataFrame:
    """Ensure every (zone, hour) combination exists, with demand=0 for silent hours."""
    zones = agg["zone_id"].unique()
    full_hours = pd.date_range(agg["pickup_hour"].min(), agg["pickup_hour"].max(), freq="h")
    idx = pd.MultiIndex.from_product([zones, full_hours], names=["zone_id", "pickup_hour"])
    full = pd.DataFrame(index=idx).reset_index()

    merged = full.merge(agg, on=["zone_id", "pickup_hour"], how="left")
    merged["demand"] = merged["demand"].fillna(0).astype(int)
    for col in ["avg_fare", "avg_distance", "avg_passengers"]:
        merged[col] = merged[col].fillna(merged[col].median())
    return merged


def main():
    print("Loading raw trip data...")
    raw = load_raw()
    print(f"Loaded {len(raw):,} raw rows")

    cleaned = clean_trips(raw)
    agg = aggregate_zone_hour(cleaned)
    full = fill_zone_hour_grid(agg)

    zones = pd.read_csv(RAW_DIR / "taxi_zones.csv")
    full = full.merge(zones, left_on="zone_id", right_on="LocationID", how="left").drop(columns=["LocationID"])

    out_path = PROC_DIR / "zone_hour_demand.parquet"
    full.to_parquet(out_path, index=False)
    print(f"Wrote {len(full):,} zone-hour rows -> {out_path}")
    print(full.head())


if __name__ == "__main__":
    main()
