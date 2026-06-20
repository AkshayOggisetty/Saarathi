"""Pre-score every historical event for the dashboard map layer."""
import os, sys
import pandas as pd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from models.predict import score_batch

df = pd.read_csv(os.path.join(HERE, "data", "processed", "events_clean.csv"))
scored = score_batch(df)
out = os.path.join(HERE, "data", "processed", "events_scored.csv")
scored.to_csv(out, index=False)
print(f"SCORED {len(scored)} rows -> {out}")
print(scored["severity"].value_counts().to_dict())
print("mean impact:", round(scored.impact_score.mean(), 1))
