"""
generate_raw_data.py
---------------------
Generates a synthetic but statistically realistic NYC TLC-style yellow-taxi
trip dataset: same columns, same kinds of data-quality problems (missing
values, negative fares, zero-distance trips, bad timestamps) as the real
TLC Trip Record Data.

Why synthetic: the real TLC files are hosted on domains outside this
environment's network allowlist. Every downstream script (cleaning,
feature engineering, training, API) is written against the real TLC
schema, so pointing them at actual monthly parquet files from
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page requires no
code changes -- just drop the files into data/raw/ and re-run.
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# A realistic subset of real NYC TLC taxi zones (LocationID, Zone, Borough)
# ---------------------------------------------------------------------------
ZONES = [
    (4,   "Alphabet City",            "Manhattan", 1.00),
    (7,   "Astoria",                  "Queens",    0.55),
    (13,  "Battery Park City",        "Manhattan", 0.85),
    (24,  "Bloomingdale",             "Manhattan", 0.75),
    (33,  "Brooklyn Heights",         "Brooklyn",  0.60),
    (42,  "Central Harlem",           "Manhattan", 0.65),
    (48,  "Clinton East",             "Manhattan", 1.15),
    (50,  "Clinton West",             "Manhattan", 1.05),
    (68,  "East Chelsea",             "Manhattan", 1.10),
    (79,  "East Village",             "Manhattan", 1.20),
    (87,  "Financial District North", "Manhattan", 1.30),
    (90,  "Flatiron",                 "Manhattan", 1.25),
    (100, "Garment District",         "Manhattan", 1.10),
    (107, "Gramercy",                 "Manhattan", 1.00),
    (113, "Greenwich Village North",  "Manhattan", 1.05),
    (114, "Greenwich Village South",  "Manhattan", 1.00),
    (125, "Hudson Sq",                "Manhattan", 0.95),
    (132, "JFK Airport",              "Queens",    1.40),
    (138, "LaGuardia Airport",        "Queens",    1.20),
    (140, "Lenox Hill East",          "Manhattan", 0.90),
    (141, "Lenox Hill West",          "Manhattan", 0.90),
    (142, "Lincoln Square East",      "Manhattan", 1.00),
    (148, "Lower East Side",          "Manhattan", 0.95),
    (161, "Midtown Center",           "Manhattan", 1.45),
    (162, "Midtown East",             "Manhattan", 1.40),
    (163, "Midtown North Center",     "Manhattan", 1.35),
    (164, "Midtown South",            "Manhattan", 1.30),
    (170, "Murray Hill",              "Manhattan", 1.05),
    (186, "Penn Station/Madison Sq West", "Manhattan", 1.35),
    (211, "SoHo",                     "Manhattan", 1.15),
    (224, "Stuy Town/Peter Cooper Village", "Manhattan", 0.70),
    (229, "Sutton Place/Turtle Bay North",  "Manhattan", 0.90),
    (230, "Times Sq/Theatre District", "Manhattan", 1.50),
    (231, "TriBeCa/Civic Center",      "Manhattan", 1.00),
    (234, "Union Sq",                 "Manhattan", 1.20),
    (236, "Upper East Side North",    "Manhattan", 1.10),
    (237, "Upper East Side South",    "Manhattan", 1.15),
    (238, "Upper West Side North",    "Manhattan", 0.95),
    (239, "Upper West Side South",    "Manhattan", 0.95),
    (249, "West Village",             "Manhattan", 1.05),
]
ZONE_IDS = [z[0] for z in ZONES]
ZONE_LOOKUP = {z[0]: (z[1], z[2], z[3]) for z in ZONES}

START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2024-04-30 23:00:00")
HOURS = pd.date_range(START, END, freq="h")

HOLIDAYS_2024 = pd.to_datetime([
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-31",
])


def hour_multiplier(hour: int) -> float:
    # bimodal commute pattern: morning + evening peaks, deep-night lull
    curve = {
        0: 0.35, 1: 0.22, 2: 0.15, 3: 0.10, 4: 0.12, 5: 0.20,
        6: 0.45, 7: 0.85, 8: 1.15, 9: 1.00, 10: 0.80, 11: 0.78,
        12: 0.90, 13: 0.88, 14: 0.85, 15: 0.90, 16: 1.00, 17: 1.25,
        18: 1.40, 19: 1.30, 20: 1.10, 21: 0.95, 22: 0.80, 23: 0.55,
    }
    return curve[hour]


def dow_multiplier(dow: int, hour: int) -> float:
    # 0=Mon ... 6=Sun. Weekend late nights spike, weekend mornings are quiet.
    if dow < 5:
        return 1.0
    if hour in (22, 23, 0, 1, 2):
        return 1.35
    if hour in range(6, 11):
        return 0.55
    return 0.85


def generate_zone_hour_lambda(zone_popularity: float, ts: pd.Timestamp) -> float:
    base = 9.0 * zone_popularity
    hm = hour_multiplier(ts.hour)
    dm = dow_multiplier(ts.dayofweek, ts.hour)
    holiday = 0.6 if ts.normalize() in HOLIDAYS_2024 else 1.0
    # mild weather proxy: a handful of "rainy" days each month bump demand ~15%
    rain = 1.15 if (ts.dayofyear % 11 == 0) else 1.0
    noise = RNG.normal(1.0, 0.08)
    return max(base * hm * dm * holiday * rain * noise, 0.05)


def main():
    print(f"Generating synthetic trips for {len(ZONE_IDS)} zones x {len(HOURS)} hours ...")
    rows = []
    trip_id = 0
    for ts in HOURS:
        for zid in ZONE_IDS:
            _, _, pop = ZONE_LOOKUP[zid]
            lam = generate_zone_hour_lambda(pop, ts)
            n_trips = RNG.poisson(lam)
            if n_trips == 0:
                continue
            # pickup offsets within the hour
            offsets = RNG.integers(0, 3600, size=n_trips)
            for off in offsets:
                pickup_dt = ts + pd.Timedelta(seconds=int(off))
                trip_minutes = max(RNG.normal(14, 8), 1.5)
                dropoff_dt = pickup_dt + pd.Timedelta(minutes=trip_minutes)
                # destination zone: mostly nearby/popular zones
                do_zid = RNG.choice(ZONE_IDS, p=_dest_probs(zid))
                distance = max(RNG.gamma(2.0, 1.4), 0.2)
                fare = round(2.5 + distance * 3.1 + trip_minutes * 0.35 + RNG.normal(0, 1.2), 2)
                passenger_count = RNG.choice([1, 1, 1, 2, 2, 3, 4], p=None)
                rows.append((
                    trip_id, pickup_dt, dropoff_dt, zid, do_zid,
                    passenger_count, round(distance, 2), fare
                ))
                trip_id += 1
        if ts.day == 1 and ts.hour == 0:
            print(f"  ... reached {ts.date()}")

    df = pd.DataFrame(rows, columns=[
        "trip_id", "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "PULocationID", "DOLocationID", "passenger_count",
        "trip_distance", "fare_amount",
    ])

    df = _inject_data_quality_issues(df)

    out_path = OUT_DIR / "yellow_tripdata_synthetic_2024.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df):,} raw trip rows -> {out_path}")

    zones_path = OUT_DIR / "taxi_zones.csv"
    pd.DataFrame(ZONES, columns=["LocationID", "Zone", "Borough", "PopularityIndex"]).to_csv(zones_path, index=False)
    print(f"Wrote zone lookup -> {zones_path}")


_DEST_CACHE = {}
def _dest_probs(pickup_zid):
    if pickup_zid in _DEST_CACHE:
        return _DEST_CACHE[pickup_zid]
    pops = np.array([ZONE_LOOKUP[z][2] for z in ZONE_IDS])
    p = pops / pops.sum()
    _DEST_CACHE[pickup_zid] = p
    return p


def _inject_data_quality_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Mimic real-world TLC data-quality problems so the cleaning step earns its keep."""
    n = len(df)
    idx = RNG.choice(n, size=int(n * 0.015), replace=False)
    df.loc[idx, "fare_amount"] = -RNG.uniform(1, 20, size=len(idx))  # negative fares

    idx = RNG.choice(n, size=int(n * 0.01), replace=False)
    df.loc[idx, "trip_distance"] = 0.0  # zero-distance trips

    idx = RNG.choice(n, size=int(n * 0.008), replace=False)
    df.loc[idx, "passenger_count"] = np.nan  # missing passenger counts

    idx = RNG.choice(n, size=int(n * 0.005), replace=False)
    df.loc[idx, "trip_distance"] = RNG.uniform(200, 500, size=len(idx))  # absurd distances

    idx = RNG.choice(n, size=int(n * 0.003), replace=False)
    # dropoff before pickup
    df.loc[idx, "tpep_dropoff_datetime"] = df.loc[idx, "tpep_pickup_datetime"] - pd.Timedelta(minutes=10)

    return df


if __name__ == "__main__":
    main()
