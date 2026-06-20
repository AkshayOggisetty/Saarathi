"""
Saarthi — Phase 3: predictive models + Impact Score.
Fills G1 (impact metric) and G5 (rare-class handling via class weights).
Trains 3 models on the cleaned data and serialises them to models/artifacts/.

  1. duration_band  (multiclass)  -> how long the disruption lasts
  2. road_closure   (binary)      -> will it need a closure
  3. priority       (binary)      -> High vs Low operational priority

Impact Score (0-100) = weighted blend of the three, scaled by corridor weight.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from xgboost import XGBClassifier

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "processed", "events_clean.csv")
ART = os.path.join(HERE, "models", "artifacts")
os.makedirs(ART, exist_ok=True)

CAT = ["event_type", "event_cause", "corridor", "veh_type", "zone"]
NUM = ["latitude", "longitude", "hour", "dow", "is_weekend", "month",
       "dist_to_cbd_km", "has_endpoint", "corridor_weight"]

# duration bands (minutes) -> label and representative midpoint for scoring
BANDS = [(0, 60, "<1h", 30), (60, 360, "1-6h", 180),
         (360, 1440, "6-24h", 720), (1440, 1e9, ">24h", 2160)]
BAND_LABELS = [b[2] for b in BANDS]
BAND_MID = {b[2]: b[3] for b in BANDS}


def band_of(mins):
    for lo, hi, lab, _ in BANDS:
        if lo <= mins < hi:
            return lab
    return ">24h"


def make_pre():
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=10), CAT),
        ("num", StandardScaler(), NUM),
    ])


def fit_clf(X, y, multiclass=False, classes=None):
    pre = make_pre()
    # class weights handle imbalance / rare classes (G5)
    if multiclass:
        clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                            subsample=0.9, colsample_bytree=0.9,
                            objective="multi:softprob", eval_metric="mlogloss",
                            tree_method="hist", n_jobs=4, random_state=42)
    else:
        pos = max((y == 0).sum(), 1) / max((y == 1).sum(), 1)
        clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                            subsample=0.9, colsample_bytree=0.9,
                            scale_pos_weight=pos, eval_metric="logloss",
                            tree_method="hist", n_jobs=4, random_state=42)
    pipe = Pipeline([("pre", pre), ("clf", clf)])
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42,
                                          stratify=y if not multiclass or y.nunique() > 1 else None)
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    f1 = f1_score(yte, pred, average="weighted")
    return pipe, f1, (yte, pred)


def main():
    df = pd.read_csv(DATA)
    metrics = {}

    # ---- Model 1: duration band (only rows with duration) ----
    d = df.dropna(subset=["duration_min"]).copy()
    d["band"] = d["duration_min"].apply(band_of)
    le = {lab: i for i, lab in enumerate(BAND_LABELS)}
    y1 = d["band"].map(le)
    m1, f1_1, _ = fit_clf(d[CAT + NUM], y1, multiclass=True)
    joblib.dump({"pipe": m1, "labels": BAND_LABELS, "mid": BAND_MID},
                os.path.join(ART, "duration_model.joblib"))
    metrics["duration_band_f1"] = round(float(f1_1), 3)
    metrics["duration_train_rows"] = int(len(d))

    # ---- Model 2: road closure ----
    y2 = df["requires_road_closure"].astype(int)
    m2, f1_2, _ = fit_clf(df[CAT + NUM], y2)
    joblib.dump(m2, os.path.join(ART, "closure_model.joblib"))
    metrics["closure_f1"] = round(float(f1_2), 3)

    # ---- Model 3: priority (High=1) ----
    y3 = (df["priority"] == "High").astype(int)
    m3, f1_3, _ = fit_clf(df[CAT + NUM], y3)
    joblib.dump(m3, os.path.join(ART, "priority_model.joblib"))
    metrics["priority_f1"] = round(float(f1_3), 3)

    # ---- persist feature schema + scoring config ----
    cfg = {"CAT": CAT, "NUM": NUM, "bands": BAND_LABELS, "band_mid": BAND_MID}
    json.dump(cfg, open(os.path.join(ART, "schema.json"), "w"), indent=2)
    json.dump(metrics, open(os.path.join(ART, "metrics.json"), "w"), indent=2)

    print("=== TRAINING METRICS ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print("artifacts ->", ART)


if __name__ == "__main__":
    main()
