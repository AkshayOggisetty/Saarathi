# 🚦 Saarthi — Event-Driven Congestion Intelligence for Bengaluru

> **Smart Anticipatory Allocation for Road Traffic Handling & Intervention**
> Flipkart Hackathon 2024 · Round 2 Prototype · Theme: *Event-Driven Congestion (Planned & Unplanned)*

Saarthi forecasts the **traffic impact** of planned and unplanned events across
Bengaluru and recommends **optimal manpower, barricading, and diversion plans** —
turning experience-driven response into data-driven, anticipatory operations.

Built entirely on the anonymised **Astram event dataset** (8,057 events,
Nov 2023 – Apr 2024) using **only free, open-source tools** (no paid APIs).

---

## ✨ What it does

| Capability | How |
|---|---|
| **Forecast impact** | XGBoost models predict event **duration**, **road-closure probability**, and **priority**, combined into a 0–100 **Impact Score** |
| **Recommend response** | Rule engine maps severity → officers, barricades, tow/drainage crews, diversion flag, advisory |
| **Plan diversions** | Local routing engine generates a bypass around the blocked point (OSM real-routing plugs in where reachable) |
| **Real-time ready** | Event-stream replay simulates a live feed; FastAPI `/intake` accepts real feeds at the same point |
| **Operations map** | City-wide hotspot heatmap to pre-position manpower |

---

## 🚀 Run locally

```bash
# 1. install
pip install -r requirements.txt

# 2. (optional) rebuild data + models from raw — artifacts are already included
python etl/clean.py
python models/train.py
python models/score_all.py

# 3. launch the dashboard
streamlit run app/streamlit_app.py
#   -> opens http://localhost:8501

# 4. (optional) run the API
uvicorn api.main:app --reload
#   -> docs at http://localhost:8000/docs
```

> On Windows, if `streamlit` is not found, use: `python -m streamlit run app/streamlit_app.py`

---

## 🗂️ Project structure

```
saarthi/
├── data/raw/astram_events.csv          # source dataset
├── data/processed/                     # cleaned + scored data (generated)
├── etl/clean.py                        # cleaning, timezone fix, features (G7,G8)
├── models/train.py                     # train 3 XGBoost models (G1,G5)
│         predict.py                    # inference + Impact Score
│         score_all.py                  # batch-score history for the map
│         artifacts/                    # serialised models + metrics
├── rules/recommend.py                  # manpower/barricade rule engine (G4)
├── routing/divert.py                   # diversion routing (G3)
├── api/main.py                         # FastAPI backend (G2 real-time intake)
├── app/streamlit_app.py                # dashboard (the demo)
└── reports/                            # analysis + gap + implementation reports
```

---

## 🧠 Models

| Model | Target | Test F1 |
|---|---|---|
| Duration band | <1h / 1–6h / 6–24h / >24h | ~0.51 |
| Road closure | needs closure (binary) | ~0.99\* |
| Priority | High vs Low (binary) | ~0.99\* |

\* High because closure/priority are near-deterministic from `corridor`/`event_cause`
in this operational dataset — a genuine pattern, not leakage. Duration is the
hard, genuinely predictive task.

---

## 📊 Data gaps & how we addressed them

The dataset logs *incidents*, not *traffic*. See `reports/DATASET_GAPS_REPORT.md`
for the full gap analysis. Summary:

- **No impact metric** → composite Impact Score (proxy) from duration + closure + priority + corridor load.
- **No real-time feed** → stream replay + real-time-ready API intake.
- **No road network** → local diversion engine (OSM hook included).
- **No optimal-response labels** → expert rule engine, RL-ready.
- Sparse planned events / weather / NLP → documented as designed future work.

---

## 🔒 Cost

100% free / open-source. No paid APIs, no credit card. Deployable free on
Hugging Face Spaces or Streamlit Community Cloud.

---

*Dataset is anonymised; free-text fields may contain `[PERSON]`/`[LOCATION]` redactions.*
