"""
Saarthi — Phase 1: Data cleaning + feature engineering.
Fills gaps G7 (timezone) and G8 (missingness/imputation).
Reads data/raw/astram_events.csv -> writes data/processed/events_clean.parquet (+ csv).
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "raw", "astram_events.csv")
OUT_DIR = os.path.join(HERE, "data", "processed")
os.makedirs(OUT_DIR, exist_ok=True)

# Bengaluru city centre (MG Road approx) for distance feature
CBD = (12.9759, 77.6045)
BBOX = dict(lat=(12.7, 13.3), lon=(77.3, 77.9))


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * R * np.arcsin(np.sqrt(a))


def load_raw():
    df = pd.read_csv(RAW, dtype=str, keep_default_na=False)
    return df.replace({"NULL": np.nan, "": np.nan})


def clean(df):
    # ---- drop 100%-empty / useless columns (G8) ----
    drop_cols = ["map_file", "comment", "meta_data"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # ---- numeric coords ----
    for c in ["latitude", "longitude", "endlatitude", "endlongitude"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # keep only rows inside Bengaluru bbox
    df = df[df.latitude.between(*BBOX["lat"]) & df.longitude.between(*BBOX["lon"])].copy()

    # ---- timestamps + timezone fix (G7) ----
    # raw stamps are UTC; convert to IST for human-meaningful time features
    for c in ["start_datetime", "end_datetime", "created_date",
              "resolved_datetime", "closed_datetime", "modified_datetime"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    df["start_ist"] = df["start_datetime"].dt.tz_convert("Asia/Kolkata")

    # ---- duration label (best available end timestamp) ----
    end_eff = (df.get("resolved_datetime")
               .fillna(df.get("closed_datetime"))
               .fillna(df.get("end_datetime")))
    dur = (end_eff - df["start_datetime"]).dt.total_seconds() / 60.0
    df["duration_min"] = dur.where((dur > 0) & (dur < 60 * 24 * 7))

    # ---- categorical normalisation (G8 imputation) ----
    df["event_type"] = df["event_type"].where(df["event_type"].isin(["planned", "unplanned"]))
    # canonical event causes; rare/garbage -> 'others'
    valid_causes = {
        "vehicle_breakdown", "pot_holes", "construction", "water_logging", "accident",
        "tree_fall", "road_conditions", "congestion", "public_event", "procession",
        "vip_movement", "protest", "others",
    }
    df["event_cause"] = df["event_cause"].where(df["event_cause"].isin(valid_causes), "others")

    df["requires_road_closure"] = (df["requires_road_closure"]
                                   .map({"TRUE": 1, "FALSE": 0}))
    df["requires_road_closure"] = df["requires_road_closure"].fillna(0).astype(int)

    df["priority"] = df["priority"].where(df["priority"].isin(["High", "Low"])).fillna("Low")
    df["corridor"] = df["corridor"].fillna("Non-corridor")
    df["veh_type"] = df["veh_type"].fillna("unknown")
    df["police_station"] = df["police_station"].fillna("Unknown")
    df["zone"] = df["zone"].fillna("Unknown")

    # ---- engineered features ----
    df["hour"] = df["start_ist"].dt.hour
    df["dow"] = df["start_ist"].dt.dayofweek
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    df["month"] = df["start_ist"].dt.month
    df["dist_to_cbd_km"] = haversine(df.latitude, df.longitude, CBD[0], CBD[1]).round(2)
    df["has_endpoint"] = ((df["endlatitude"].fillna(0) != 0)
                          & (df["endlongitude"].fillna(0) != 0)).astype(int)

    # corridor event-density weight (G1 input, dataset-derived = free)
    cw = df["corridor"].value_counts(normalize=True)
    df["corridor_weight"] = df["corridor"].map(cw).fillna(cw.min())

    df["impute_flag_time"] = df["start_ist"].isna().astype(int)
    df = df.dropna(subset=["start_ist", "latitude", "longitude", "event_type"])
    return df


def main():
    raw = load_raw()
    df = clean(raw)
    keep = [
        "id", "event_type", "event_cause", "latitude", "longitude",
        "endlatitude", "endlongitude", "requires_road_closure", "priority",
        "corridor", "corridor_weight", "veh_type", "police_station", "zone",
        "address", "start_ist", "hour", "dow", "is_weekend", "month",
        "dist_to_cbd_km", "has_endpoint", "duration_min", "status",
    ]
    out = df[[c for c in keep if c in df.columns]].copy()
    pq = os.path.join(OUT_DIR, "events_clean.parquet")
    csv = os.path.join(OUT_DIR, "events_clean.csv")
    try:
        out.to_parquet(pq, index=False)
    except Exception as e:
        print("parquet skip:", e)
    out.to_csv(csv, index=False)
    print(f"CLEAN OK  rows={len(out)}  cols={len(out.columns)}")
    print(f"  planned/unplanned: {out.event_type.value_counts().to_dict()}")
    print(f"  road_closure=1: {int(out.requires_road_closure.sum())}")
    print(f"  duration available: {out.duration_min.notna().sum()}")
    print(f"  written -> {csv}")


if __name__ == "__main__":
    main()
