"""
allocation.py
--------------
Turns predicted zone demand into fleet allocation recommendations.

Simple, explainable heuristic (deliberately not another ML model so
operators can see exactly why a recommendation was made):
  1. Predict demand for every zone at the requested time.
  2. Split the total available fleet across zones proportionally to
     predicted demand share.
  3. Flag zones whose predicted demand exceeds their fair share of the
     fleet as "understaffed" relative to a naive even split, and vice
     versa, so operators can see where to reposition vehicles from/to.
"""
from typing import List, Dict


def allocate_fleet(predictions: Dict[int, float], zone_lookup: Dict[int, dict],
                    total_vehicles: int) -> List[dict]:
    total_demand = sum(predictions.values()) or 1.0
    n_zones = len(predictions)
    even_share = total_vehicles / n_zones if n_zones else 0

    rows = []
    for zid, demand in predictions.items():
        share = demand / total_demand
        recommended = round(share * total_vehicles)
        meta = zone_lookup.get(zid, {})
        delta = recommended - even_share
        if delta > even_share * 0.25:
            status = "reposition_in"
        elif delta < -even_share * 0.25:
            status = "reposition_out"
        else:
            status = "balanced"
        rows.append({
            "zone_id": zid,
            "zone_name": meta.get("Zone", f"Zone {zid}"),
            "borough": meta.get("Borough", "Unknown"),
            "predicted_demand": round(demand, 1),
            "demand_share_pct": round(share * 100, 1),
            "recommended_vehicles": int(recommended),
            "status": status,
        })

    rows.sort(key=lambda r: r["predicted_demand"], reverse=True)

    # fix rounding drift so recommended vehicles sum to total_vehicles
    diff = total_vehicles - sum(r["recommended_vehicles"] for r in rows)
    i = 0
    while diff != 0 and rows:
        step = 1 if diff > 0 else -1
        rows[i % len(rows)]["recommended_vehicles"] = max(0, rows[i % len(rows)]["recommended_vehicles"] + step)
        diff -= step
        i += 1

    return rows
