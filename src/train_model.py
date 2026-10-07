"""
train_model.py
---------------
Stage 3 of the FleetIQ pipeline: train tree-based regressors to predict
zone-hour ride demand, evaluate with MAE / RMSE / R^2, and persist the
best-performing model plus its metadata for the FastAPI backend.

Train/test split is time-based (last 3 weeks held out) rather than random,
since this is a forecasting problem and random splits would leak future
information through the lag/rolling features.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import xgboost as xgb
import lightgbm as lgb
import joblib

BASE = Path(__file__).resolve().parents[1]
PROC_DIR = BASE / "data" / "processed"
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURE_COLS = [
    "hour", "day_of_week", "day_of_month", "month", "is_weekend", "is_holiday",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_rainy",
    "lag_1h", "lag_24h", "lag_168h",
    "roll_mean_3h", "roll_mean_24h", "roll_mean_168h", "roll_std_24h",
    "zone_avg_demand", "borough_code", "PopularityIndex",
    "avg_fare", "avg_distance", "avg_passengers",
    "zone_id",
]
TARGET_COL = "demand"


def time_based_split(df: pd.DataFrame, holdout_days: int = 21):
    cutoff = df["pickup_hour"].max() - pd.Timedelta(days=holdout_days)
    train = df[df["pickup_hour"] <= cutoff]
    test = df[df["pickup_hour"] > cutoff]
    return train, test


def evaluate(y_true, y_pred, label):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    print(f"  [{label}] MAE={mae:.3f}  RMSE={rmse:.3f}  R2={r2:.4f}")
    return {"mae": mae, "rmse": rmse, "r2": r2}


def main():
    print("Loading model features...")
    df = pd.read_parquet(PROC_DIR / "model_features.parquet")

    train, test = time_based_split(df)
    print(f"Train rows: {len(train):,}  Test rows: {len(test):,} "
          f"(split at {train['pickup_hour'].max()})")

    X_train, y_train = train[FEATURE_COLS], train[TARGET_COL]
    X_test, y_test = test[FEATURE_COLS], test[TARGET_COL]

    results = {}

    print("\nTraining XGBoost...")
    xgb_model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror",
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = np.clip(xgb_model.predict(X_test), 0, None)
    results["xgboost"] = evaluate(y_test, xgb_pred, "XGBoost")

    print("\nTraining LightGBM...")
    lgb_model = lgb.LGBMRegressor(
        n_estimators=500,
        max_depth=-1,
        num_leaves=48,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_samples=15,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )
    lgb_model.fit(X_train, y_train)
    lgb_pred = np.clip(lgb_model.predict(X_test), 0, None)
    results["lightgbm"] = evaluate(y_test, lgb_pred, "LightGBM")

    # model selection: lowest RMSE wins
    best_name = min(results, key=lambda k: results[k]["rmse"])
    best_model = xgb_model if best_name == "xgboost" else lgb_model
    print(f"\nSelected model: {best_name} (RMSE={results[best_name]['rmse']:.3f})")

    joblib.dump(best_model, MODEL_DIR / "demand_model.joblib")
    joblib.dump(FEATURE_COLS, MODEL_DIR / "feature_columns.joblib")

    # zone metadata for the API (id -> name/borough/avg demand/popularity)
    zone_meta = (
        df.groupby("zone_id")
        .agg(
            Zone=("Zone", "first"),
            Borough=("Borough", "first"),
            PopularityIndex=("PopularityIndex", "first"),
            avg_demand=("demand", "mean"),
        )
        .reset_index()
        .to_dict(orient="records")
    )

    # most recent feature row per zone -> used by the API to build live
    # predictions for "now" / arbitrary future timestamps without needing
    # a database.
    latest = (
        df.sort_values("pickup_hour")
        .groupby("zone_id")
        .tail(168)  # keep last week per zone so the API can recompute lags
        [["zone_id", "pickup_hour", "demand"] + [c for c in FEATURE_COLS if c not in ("hour", "day_of_week", "day_of_month", "month", "is_weekend", "is_holiday", "hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_rainy", "zone_id")]]
    )

    latest.to_parquet(MODEL_DIR / "latest_zone_history.parquet", index=False)

    metadata = {
        "best_model": best_name,
        "metrics": results,
        "feature_columns": FEATURE_COLS,
        "target_column": TARGET_COL,
        "train_rows": len(train),
        "test_rows": len(test),
        "trained_through": str(df["pickup_hour"].max()),
        "zones": zone_meta,
    }
    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # actual-vs-predicted sample for the dashboard (best model, test period,
    # aggregated to city-wide hourly totals so it's a manageable payload)
    test = test.copy()
    test["predicted"] = xgb_pred if best_name == "xgboost" else lgb_pred
    avp = (
        test.groupby("pickup_hour")
        .agg(actual=("demand", "sum"), predicted=("predicted", "sum"))
        .reset_index()
    )
    avp.to_parquet(MODEL_DIR / "actual_vs_predicted.parquet", index=False)

    print(f"\nSaved model + metadata to {MODEL_DIR}")


if __name__ == "__main__":
    main()
