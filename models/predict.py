"""
Saarathi — inference + Impact Score (G1).
Loads trained artifacts and scores a single event (dict) or a DataFrame.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

_cfg = json.load(open(os.path.join(ART, "schema.json")))
CAT, NUM = _cfg["CAT"], _cfg["NUM"]
BAND_MID = _cfg["band_mid"]

_dur = joblib.load(os.path.join(ART, "duration_model.joblib"))
_clo = joblib.load(os.path.join(ART, "closure_model.joblib"))
_pri = joblib.load(os.path.join(ART, "priority_model.joblib"))

# max expected duration (>24h midpoint) used to normalise the score
_MAX_MID = max(BAND_MID.values())


def _frame(event: dict) -> pd.DataFrame:
    row = {c: event.get(c, "unknown") for c in CAT}
    for n in NUM:
        row[n] = event.get(n, 0)
    return pd.DataFrame([row])


def score_event(event: dict) -> dict:
    """event keys: event_type, event_cause, corridor, veh_type, zone,
    latitude, longitude, hour, dow, is_weekend, month, dist_to_cbd_km,
    has_endpoint, corridor_weight."""
    X = _frame(event)

    # duration band + expected minutes
    dur_model = _dur["pipe"]
    labels = _dur["labels"]
    proba = dur_model.predict_proba(X)[0]
    band_idx = int(np.argmax(proba))
    band = labels[band_idx]
    exp_minutes = float(sum(proba[i] * BAND_MID[labels[i]] for i in range(len(labels))))

    p_closure = float(_clo.predict_proba(X)[0][1])
    p_high = float(_pri.predict_proba(X)[0][1])

    # ---- Impact Score 0-100 (G1) ----
    dur_term = np.log1p(exp_minutes) / np.log1p(_MAX_MID)        # 0..1
    cw = float(event.get("corridor_weight", 0.0))
    cw_norm = min(cw / 0.10, 1.0)                                 # busy corridor boost
    score = 100 * (0.45 * dur_term + 0.30 * p_closure
                   + 0.15 * p_high + 0.10 * cw_norm)
    score = round(min(max(score, 0), 100), 1)

    sev = ("Critical" if score >= 70 else "High" if score >= 50
           else "Moderate" if score >= 30 else "Low")
    return {
        "impact_score": score,
        "severity": sev,
        "duration_band": band,
        "expected_minutes": round(exp_minutes),
        "p_road_closure": round(p_closure, 3),
        "p_high_priority": round(p_high, 3),
    }


def score_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorised scoring for many rows (used for the historical map layer)."""
    X = df.copy()
    for c in CAT:
        if c not in X:
            X[c] = "unknown"
    for n in NUM:
        if n not in X:
            X[n] = 0
    X = X[CAT + NUM]

    labels = _dur["labels"]
    proba = _dur["pipe"].predict_proba(X)
    mids = np.array([BAND_MID[l] for l in labels])
    exp_minutes = proba @ mids
    band_idx = proba.argmax(axis=1)
    band = np.array(labels)[band_idx]

    p_closure = _clo.predict_proba(X)[:, 1]
    p_high = _pri.predict_proba(X)[:, 1]

    dur_term = np.log1p(exp_minutes) / np.log1p(_MAX_MID)
    cw = df.get("corridor_weight", pd.Series(0, index=df.index)).fillna(0).values
    cw_norm = np.minimum(cw / 0.10, 1.0)
    score = 100 * (0.45 * dur_term + 0.30 * p_closure + 0.15 * p_high + 0.10 * cw_norm)
    score = np.clip(score, 0, 100).round(1)

    sev = np.where(score >= 70, "Critical",
          np.where(score >= 50, "High",
          np.where(score >= 30, "Moderate", "Low")))

    out = df.copy()
    out["impact_score"] = score
    out["severity"] = sev
    out["duration_band"] = band
    out["expected_minutes"] = exp_minutes.round().astype(int)
    out["p_road_closure"] = p_closure.round(3)
    out["p_high_priority"] = p_high.round(3)
    return out


if __name__ == "__main__":
    demo = dict(event_type="planned", event_cause="procession", corridor="Mysore Road",
                veh_type="unknown", zone="West Zone 1", latitude=12.95, longitude=77.53,
                hour=18, dow=5, is_weekend=1, month=3, dist_to_cbd_km=8.0,
                has_endpoint=1, corridor_weight=0.09)
    print(json.dumps(score_event(demo), indent=2))
