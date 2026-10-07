"""
model_service.py
-----------------
Loads the trained demand model and the artifacts produced by
src/train_model.py, and provides feature preparation + inference used by
the FastAPI routes.
"""
import json
from datetime import datetime
from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
import joblib

BASE = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE / "models"

HOLIDAYS_2024 = pd.to_datetime([
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-31",
])


class DemandModelService:
    def __init__(self):
        self.model = joblib.load(MODEL_DIR / "demand_model.joblib")
        self.feature_columns = joblib.load(MODEL_DIR / "feature_columns.joblib")
        with open(MODEL_DIR / "metadata.json") as f:
            self.metadata = json.load(f)
        self.zone_history = pd.read_parquet(MODEL_DIR / "latest_zone_history.parquet")
        self.zones_df = pd.DataFrame(self.metadata["zones"])
        avp = pd.read_parquet(MODEL_DIR / "actual_vs_predicted.parquet")
        avp["pickup_hour"] = pd.to_datetime(avp["pickup_hour"])
        self.actual_vs_predicted = avp.sort_values("pickup_hour")

        # city-wide average demand, used to classify demand levels
        self.demand_thresholds = self._compute_thresholds()

    def _compute_thresholds(self):
        vals = self.zone_history["demand"]
        return {
            "low": float(vals.quantile(0.33)),
            "medium": float(vals.quantile(0.66)),
            "high": float(vals.quantile(0.90)),
        }

    def demand_level(self, value: float) -> str:
        t = self.demand_thresholds
        if value <= t["low"]:
            return "low"
        if value <= t["medium"]:
            return "medium"
        if value <= t["high"]:
            return "high"
        return "very_high"

    def list_zones(self):
        return self.zones_df.to_dict(orient="records")

    def _zone_recent(self, zone_id: int) -> pd.DataFrame:
        h = self.zone_history[self.zone_history["zone_id"] == zone_id].sort_values("pickup_hour")
        if h.empty:
            raise ValueError(f"Unknown zone_id: {zone_id}")
        return h

    def build_features(self, zone_id: int, ts: datetime) -> pd.DataFrame:
        """Build a single-row feature vector for (zone_id, timestamp) using
        the zone's most recent known demand history for lag/rolling features."""
        hist = self._zone_recent(zone_id)
        zone_row = self.zones_df[self.zones_df["zone_id"] == zone_id].iloc[0]

        ts = pd.Timestamp(ts)
        hist["pickup_hour"] = pd.to_datetime(hist["pickup_hour"])

        # Convert timestamps to integer microseconds
        hist_times = hist["pickup_hour"].astype("int64")
        ts_us = ts.to_datetime64().astype("datetime64[us]").astype("int64")

        hist_before = hist[hist_times < ts_us]

        if not hist_before.empty:
            series = hist_before.set_index("pickup_hour")["demand"]
        else:
            series = hist.set_index("pickup_hour")["demand"]

        def lag(hours):
            target = ts - pd.Timedelta(hours=hours)

            target_us = (
                target.to_datetime64()
                .astype("datetime64[us]")
                .astype("int64")
            )

            index_us = series.index.astype("int64")

            matches = series[index_us == target_us]

            if len(matches):
                return float(matches.iloc[0])

            return float(series.mean()) if len(series) else 0.0

        def rolling_mean(hours):
            start = ts - pd.Timedelta(hours=hours)

            start_us = (
                start.to_datetime64()
                .astype("datetime64[us]")
                .astype("int64")
            )

            index_us = series.index.astype("int64")

            window = series[index_us >= start_us]

            return float(window.mean()) if len(window) else float(
                series.mean() if len(series) else 0.0
            )

        def rolling_std(hours):
            start = ts - pd.Timedelta(hours=hours)

            start_us = (
                start.to_datetime64()
                .astype("datetime64[us]")
                .astype("int64")
            )

            index_us = series.index.astype("int64")

            window = series[index_us >= start_us]

            return float(window.std()) if len(window) > 1 else 0.0

        row = {
            "hour": ts.hour,
            "day_of_week": ts.dayofweek,
            "day_of_month": ts.day,
            "month": ts.month,
            "is_weekend": int(ts.dayofweek >= 5),
            "is_holiday": int(ts.normalize() in HOLIDAYS_2024),
            "hour_sin": np.sin(2 * np.pi * ts.hour / 24),
            "hour_cos": np.cos(2 * np.pi * ts.hour / 24),
            "dow_sin": np.sin(2 * np.pi * ts.dayofweek / 7),
            "dow_cos": np.cos(2 * np.pi * ts.dayofweek / 7),
            "is_rainy": int(ts.dayofyear % 11 == 0),
            "lag_1h": lag(1),
            "lag_24h": lag(24),
            "lag_168h": lag(168),
            "roll_mean_3h": rolling_mean(3),
            "roll_mean_24h": rolling_mean(24),
            "roll_mean_168h": rolling_mean(168),
            "roll_std_24h": rolling_std(24),
            "zone_avg_demand": float(zone_row["avg_demand"]),
            "borough_code": self._borough_code(zone_row["Borough"]),
            "PopularityIndex": float(zone_row["PopularityIndex"]),
            "avg_fare": float(hist["avg_fare"].mean()) if "avg_fare" in hist else 15.0,
            "avg_distance": float(hist["avg_distance"].mean()) if "avg_distance" in hist else 2.5,
            "avg_passengers": float(hist["avg_passengers"].mean()) if "avg_passengers" in hist else 1.4,
            "zone_id": zone_id,
        }

        return pd.DataFrame([row])[self.feature_columns]

    def _borough_code(self, borough: str) -> int:
        boroughs = sorted(self.zones_df["Borough"].unique())
        return boroughs.index(borough)

    def predict(self, zone_id: int, ts: datetime) -> float:
        X = self.build_features(zone_id, ts)
        pred = float(self.model.predict(X)[0])
        return max(pred, 0.0)

    def predict_many(self, zone_ids, ts: datetime):
        return {zid: self.predict(zid, ts) for zid in zone_ids}


@lru_cache(maxsize=1)
def get_service() -> "DemandModelService":
    return DemandModelService()
