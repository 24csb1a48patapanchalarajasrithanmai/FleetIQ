"""
FleetIQ backend API
--------------------
FastAPI service exposing:
  GET  /api/health
  GET  /api/zones
  GET  /api/predict?zone_id=&timestamp=
  POST /api/predict/batch
  GET  /api/demand/top-zones?timestamp=&limit=
  GET  /api/demand/hourly-pattern?zone_id=
  GET  /api/demand/actual-vs-predicted
  GET  /api/fleet/allocation?timestamp=&total_vehicles=
  GET  /api/model/info

Run with:  uvicorn app.main:app --reload --port 8000   (from backend/)
"""
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .model_service import get_service
from .allocation import allocate_fleet

app = FastAPI(
    title="FleetIQ API",
    description="Intelligent fleet demand prediction & allocation API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://fleet-iq-pearl.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BatchPredictRequest(BaseModel):
    zone_ids: List[int]
    timestamp: Optional[datetime] = None


def _parse_ts(timestamp: Optional[datetime]) -> datetime:
    return timestamp or datetime.utcnow()


@app.get("/api/health")
def health():
    svc = get_service()
    return {
        "status": "ok",
        "model": svc.metadata["best_model"],
        "trained_through": svc.metadata["trained_through"],
    }


@app.get("/api/zones")
def zones():
    svc = get_service()
    return {"zones": svc.list_zones()}


@app.get("/api/predict")
def predict(
    zone_id: int = Query(..., description="TLC LocationID"),
    timestamp: Optional[datetime] = Query(None, description="ISO timestamp; defaults to now"),
):
    svc = get_service()
    ts = _parse_ts(timestamp)
    try:
        value = svc.predict(zone_id, ts)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    zone_meta = next((z for z in svc.list_zones() if z["zone_id"] == zone_id), None)
    return {
        "zone_id": zone_id,
        "zone_name": zone_meta["Zone"] if zone_meta else None,
        "borough": zone_meta["Borough"] if zone_meta else None,
        "timestamp": ts.isoformat(),
        "predicted_demand": round(value, 1),
        "demand_level": svc.demand_level(value),
    }


@app.post("/api/predict/batch")
def predict_batch(req: BatchPredictRequest):
    svc = get_service()
    ts = _parse_ts(req.timestamp)
    results = []
    for zid in req.zone_ids:
        try:
            value = svc.predict(zid, ts)
        except ValueError:
            continue
        zone_meta = next((z for z in svc.list_zones() if z["zone_id"] == zid), None)
        results.append({
            "zone_id": zid,
            "zone_name": zone_meta["Zone"] if zone_meta else None,
            "predicted_demand": round(value, 1),
            "demand_level": svc.demand_level(value),
        })
    return {"timestamp": ts.isoformat(), "predictions": results}


@app.get("/api/demand/top-zones")
def top_zones(
    timestamp: Optional[datetime] = Query(None),
    limit: int = Query(10, ge=1, le=40),
):
    svc = get_service()
    ts = _parse_ts(timestamp)
    all_zone_ids = [z["zone_id"] for z in svc.list_zones()]
    preds = svc.predict_many(all_zone_ids, ts)
    ranked = sorted(preds.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    zone_lookup = {z["zone_id"]: z for z in svc.list_zones()}
    return {
        "timestamp": ts.isoformat(),
        "top_zones": [
            {
                "zone_id": zid,
                "zone_name": zone_lookup[zid]["Zone"],
                "borough": zone_lookup[zid]["Borough"],
                "predicted_demand": round(val, 1),
                "demand_level": svc.demand_level(val),
            }
            for zid, val in ranked
        ],
    }


@app.get("/api/demand/hourly-pattern")
def hourly_pattern(zone_id: Optional[int] = Query(None, description="Omit for city-wide pattern")):
    svc = get_service()
    ts_base = _parse_ts(None).replace(minute=0, second=0, microsecond=0)
    zone_ids = [zone_id] if zone_id is not None else [z["zone_id"] for z in svc.list_zones()]

    pattern = []
    for h in range(24):
        ts = ts_base.replace(hour=h)
        total = sum(svc.predict(zid, ts) for zid in zone_ids)
        pattern.append({"hour": h, "predicted_demand": round(total, 1)})

    peak = max(pattern, key=lambda r: r["predicted_demand"])
    return {"zone_id": zone_id, "hourly_pattern": pattern, "peak_hour": peak["hour"]}


@app.get("/api/demand/actual-vs-predicted")
def actual_vs_predicted(limit: int = Query(168, ge=1, le=2000)):
    svc = get_service()
    df = svc.actual_vs_predicted.tail(limit)
    return {
        "series": [
            {
                "timestamp": row.pickup_hour.isoformat(),
                "actual": round(float(row.actual), 1),
                "predicted": round(float(row.predicted), 1),
            }
            for row in df.itertuples()
        ]
    }


@app.get("/api/fleet/allocation")
def fleet_allocation(
    timestamp: Optional[datetime] = Query(None),
    total_vehicles: int = Query(200, ge=1, le=5000),
):
    svc = get_service()
    ts = _parse_ts(timestamp)
    all_zone_ids = [z["zone_id"] for z in svc.list_zones()]
    preds = svc.predict_many(all_zone_ids, ts)
    zone_lookup = {z["zone_id"]: z for z in svc.list_zones()}
    recs = allocate_fleet(preds, zone_lookup, total_vehicles)
    return {"timestamp": ts.isoformat(), "total_vehicles": total_vehicles, "allocations": recs}


@app.get("/api/model/info")
def model_info():
    svc = get_service()
    m = svc.metadata
    return {
        "best_model": m["best_model"],
        "metrics": m["metrics"],
        "trained_through": m["trained_through"],
        "train_rows": m["train_rows"],
        "test_rows": m["test_rows"],
        "n_zones": len(m["zones"]),
    }
