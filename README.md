# FleetIQ — Intelligent Fleet Demand Prediction & Allocation Platform

FleetIQ predicts ride demand across NYC taxi zones and time periods, and turns
those predictions into fleet allocation recommendations. It's a full pipeline:
raw trip data → cleaning & feature engineering → gradient-boosted demand
models → a FastAPI backend → a React dashboard.

```
fleetiq/
├── data/
│   ├── raw/                    # raw trip data + zone lookup
│   └── processed/              # cleaned zone-hour demand, model features
├── src/
│   ├── generate_raw_data.py    # synthetic TLC-style trip generator
│   ├── data_processing.py      # cleaning + zone/hour aggregation
│   ├── feature_engineering.py  # calendar, lag, and rolling-average features
│   └── train_model.py          # trains XGBoost + LightGBM, picks the best
├── models/                     # trained model, metadata, evaluation artifacts
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI routes
│   │   ├── model_service.py    # feature building + inference
│   │   └── allocation.py       # fleet allocation heuristic
│   └── requirements.txt
└── frontend/                   # React (Vite) dashboard
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/
```

## About the data

The pipeline is written against the real **NYC TLC Trip Record Data** schema
(`tpep_pickup_datetime`, `PULocationID`, `trip_distance`, `fare_amount`, etc.).
The actual TLC parquet files are hosted on domains this build environment
can't reach, so `src/generate_raw_data.py` generates a synthetic dataset with
the same schema, the same kinds of data-quality problems (negative fares,
zero-distance trips, missing passenger counts, bad timestamps), and a
realistic demand pattern (morning/evening commute peaks, weekend late-night
spikes, holidays, a simple rain proxy) across 40 real NYC taxi zones.

**To use real data instead:** download monthly files from
[the TLC's site](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page),
drop them in `data/raw/`, point `data_processing.py`'s `load_raw()` at them,
and re-run the pipeline — no other code changes needed, since every
downstream stage only depends on the standard TLC columns.

> **Note:** the trained model, processed features, and evaluation artifacts
> are included in this download, so the backend and frontend work immediately.
> The raw synthetic trip CSV (~60MB, regenerated in ~20s) is *not* included —
> run `python3 src/generate_raw_data.py` first if you want to re-run the full
> pipeline from scratch.

## Running the full pipeline

```bash
cd fleetiq
pip install -r backend/requirements.txt

python3 src/generate_raw_data.py     # ~800k synthetic trips, 40 zones, 4 months
python3 src/data_processing.py       # clean + aggregate to zone-hour demand
python3 src/feature_engineering.py   # calendar + lag/rolling features
python3 src/train_model.py           # trains & evaluates both models, saves the best
```

This produces, in `models/`:
- `demand_model.joblib` — the winning model (XGBoost or LightGBM, picked by RMSE)
- `metadata.json` — evaluation metrics (MAE/RMSE/R²) and zone metadata
- `latest_zone_history.parquet` — recent per-zone demand, used to build live features
- `actual_vs_predicted.parquet` — held-out test period, for the dashboard chart

With the current synthetic dataset: **LightGBM** was selected
(MAE ≈ 1.42 rides/hour, RMSE ≈ 2.08, R² ≈ 0.80 on a time-based 3-week holdout).

## Running the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Key endpoints (all under `/api`):
- `GET /predict?zone_id=&timestamp=` — predicted demand + level for one zone/time
- `GET /demand/top-zones?timestamp=&limit=` — highest-demand zones right now
- `GET /demand/hourly-pattern?zone_id=` — 24h predicted demand curve + peak hour
- `GET /demand/actual-vs-predicted` — held-out test period comparison
- `GET /fleet/allocation?timestamp=&total_vehicles=` — recommended vehicles per zone
- `GET /zones`, `GET /model/info`

Interactive docs at `http://localhost:8000/docs`.

## Running the frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL if the backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`. The dashboard defaults to a timestamp inside the
training window (`2024-04-25 18:00`) so the demo shows a realistic evening-peak
pattern; change the "Forecast time" field to explore other hours/days, or pick
a different zone from the dropdown.

## Notes on the fleet allocation logic

Allocation is a transparent heuristic rather than another model: vehicles are
split across zones proportional to predicted demand share, and zones are
flagged `reposition_in` / `reposition_out` / `balanced` relative to an even
split — so operators can see exactly why a recommendation was made, not just
trust a black box.
