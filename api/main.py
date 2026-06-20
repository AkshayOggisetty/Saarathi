"""
Saarathi — Phase 5: FastAPI backend (real-time-ready intake).
Run:  uvicorn api.main:app --reload
Docs: http://localhost:8000/docs
"""
import os, sys
from fastapi import FastAPI
from pydantic import BaseModel

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from models.predict import score_event
from rules.recommend import recommend
from routing.divert import plan_diversion

app = FastAPI(title="Saarathi API",
              description="Forecast event traffic impact + recommend response.",
              version="1.0")


class Event(BaseModel):
    event_type: str = "unplanned"
    event_cause: str = "vehicle_breakdown"
    corridor: str = "Non-corridor"
    zone: str = "Unknown"
    veh_type: str = "unknown"
    latitude: float
    longitude: float
    endlatitude: float = 0
    endlongitude: float = 0
    hour: int = 12
    dow: int = 2
    is_weekend: int = 0
    month: int = 3
    dist_to_cbd_km: float = 5.0
    has_endpoint: int = 0
    corridor_weight: float = 0.01


@app.get("/")
def health():
    return {"status": "ok", "service": "saarathi"}


@app.post("/predict")
def predict(ev: Event):
    return score_event(ev.model_dump())


@app.post("/recommend")
def recommend_ep(ev: Event):
    d = ev.model_dump()
    sc = score_event(d)
    return {"impact": sc, "recommendation": recommend(sc, d)}


@app.post("/divert")
def divert(ev: Event):
    return plan_diversion(ev.latitude, ev.longitude, ev.endlatitude, ev.endlongitude)


@app.post("/intake")
def intake(ev: Event):
    """Single real-time intake: score + recommend + diversion in one call.
    A live feed POSTs here; the dashboard consumes the response."""
    d = ev.model_dump()
    sc = score_event(d)
    rec = recommend(sc, d)
    div = plan_diversion(ev.latitude, ev.longitude) if rec["recommend_diversion"] else None
    return {"impact": sc, "recommendation": rec, "diversion": div}
