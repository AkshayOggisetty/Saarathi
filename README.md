<div align="center">

# Saarathi

### Smart Anticipatory Allocation for Road-traffic Advisory, Triage, Handling & Intervention

**Forecast the traffic impact of city events — and deploy manpower, barricades & diversions before congestion happens.**

</div>

---

## Why "Saarathi"?

*Saarathi* (सारथी) is the charioteer who guides the chariot through the battlefield — anticipating
obstacles and steering to safety. Bengaluru's traffic is that battlefield; Saarathi is the data-driven
guide that helps authorities anticipate event-driven congestion and steer resources to where they're
needed before gridlock forms.

---

## The problem

Political rallies, festivals, processions, VIP movements, construction, breakdowns and water-logging
create sudden, localized traffic breakdowns across Bengaluru. Today:

- Event impact is **not quantified in advance**
- Resource deployment is **experience-driven**, not data-driven
- There is **no post-event learning loop**

**Saarathi answers:** *How can historical data forecast event traffic impact and recommend optimal
manpower, barricading, and diversion plans?*

---

## What Saarathi does

| Capability | How it works |
|---|---|
| **Forecast impact** | Three XGBoost models predict an event's **duration**, **road-closure probability**, and **operational priority**, fused into a single **0–100 Impact Score** |
| **Recommend response** | A rule engine maps severity to **officers, barricades, tow/drainage crews, diversion flag, public advisory** |
| **Plan diversions** | A routing engine generates a **bypass around the blocked point** (real OpenStreetMap routing where reachable, local engine otherwise) |
| **Real-time ready** | An event-stream **replay simulates a live feed**; a FastAPI `/intake` endpoint accepts real feeds at the same point |
| **Operations map** | A city-wide **Impact-Score hotspot heatmap** to pre-position manpower |

Built on the anonymised **Astram dataset** — 8,057 real Bengaluru events (Nov 2023 – Apr 2024), 100% geocoded.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the dashboard (models & data are pre-built and included)
streamlit run app/streamlit_app.py
#    -> opens http://localhost:8501
#    Windows: python -m streamlit run app/streamlit_app.py

# 3. (optional) Run the REST API
uvicorn api.main:app --reload
#    -> interactive docs at http://localhost:8000/docs
```

**Rebuild from raw data (optional):**
```bash
python etl/clean.py        # clean + timezone fix + features
python models/train.py     # train the 3 models + Impact Score
python models/score_all.py # score history for the map
```

---

## The dashboard

| Tab | What you see |
|---|---|
| **Operations Map** | Predicted hotspot heatmap + severity-coloured events across Bengaluru |
| **Impact Simulator** | Enter a new/upcoming event to get an instant Impact Score, response plan & diversion route |
| **Real-Time Stream** | Events replayed in time order, scored live |
| **Insights** | Causes, corridors, severity mix, planned-vs-unplanned impact |

---

## Architecture

```
        Frontend (Streamlit + Folium map)
                     |  REST
        +------------+------------+
        |      FastAPI backend     |
        | /predict /recommend      |
        | /divert  /intake         |
        +-+----+--------+--------+-+
          |    |        |        |
     Impact   Rule    Routing  Stream
     models   engine  engine   replay
       (G1)    (G4)    (G3)     (G2)
          |
   +------+----------------------------------+
   | Astram dataset - cleaned & feature store|
   +-----------------------------------------+
```

---

## Models

| Model | Target | Test F1 |
|---|---|---|
| Duration band | `<1h / 1–6h / 6–24h / >24h` | ~0.51 |
| Road closure | needs closure (binary) | ~0.99\* |
| Priority | High vs Low (binary) | ~0.99\* |

\* High because closure & priority are **near-deterministic from `corridor` / `event_cause`** in this
operational dataset (a genuine pattern, not target leakage). **Duration** is the hard, genuinely
predictive task and drives most of the Impact Score.

---

## Honest about the data (and how we engineered around it)

The Astram dataset logs *incidents*, not *traffic measurements*. We're explicit about its limits —
see [`reports/DATASET_GAPS_REPORT.md`](reports/DATASET_GAPS_REPORT.md):

| Gap | Our approach |
|---|---|
| No traffic-impact metric | Composite **Impact Score** as a transparent proxy |
| No real-time feed | **Stream replay** + real-time-ready API intake |
| No road-network topology | **Local diversion engine** (+ OSM hook) |
| No "optimal-response" labels | **Expert rule engine**, designed RL-ready |
| Sparse events / no weather / NLP | Documented as designed **future work** |

Full analysis: [`reports/ANALYSIS_REPORT.md`](reports/ANALYSIS_REPORT.md) ·
Build plan: [`reports/IMPLEMENTATION_PLAN.md`](reports/IMPLEMENTATION_PLAN.md)

---

## Project structure

```
saarathi/
├── app/streamlit_app.py     # dashboard (the demo)
├── app.py                   # Spaces/Streamlit-Cloud entrypoint
├── api/main.py              # FastAPI backend (real-time intake)
├── etl/clean.py             # cleaning, timezone fix, features
├── models/                  # train.py · predict.py · score_all.py · artifacts/
├── rules/recommend.py       # manpower/barricade rule engine
├── routing/divert.py        # diversion routing
├── data/                    # raw + processed (included so it runs out-of-the-box)
├── reports/                 # analysis, gap & implementation reports
└── requirements.txt
```

---

<div align="center">

*Dataset is anonymised (free-text may contain `[PERSON]`/`[LOCATION]` redactions).*

**Saarathi — Anticipate the impact. Deploy with precision.**

</div>
