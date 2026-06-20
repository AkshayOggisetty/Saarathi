# Implementation Plan — Fill Every Gap
### Flipkart Hackathon, Round 2 · Event-Driven Congestion · Bengaluru
### Project codename: **Saarthi** (Smart Anticipatory Allocation for Road Traffic Handling & Intervention)

**Goal:** Build a working prototype that closes **all 10 dataset gaps (G1–G10)** and delivers the problem statement's full ask — *forecast event traffic impact + recommend optimal manpower, barricading, and diversions, using historical AND real-time data.*

**Companion docs:** `ANALYSIS_REPORT.md`, `DATASET_GAPS_REPORT.md`.

---

## 1. Target Architecture

```
                         ┌────────────────────────────────────────────┐
                         │                FRONTEND (React + Leaflet)    │
                         │  Map dashboard · Event simulator · Recs panel│
                         └───────────────▲──────────────┬──────────────┘
                                         │ REST/WebSocket │
                         ┌───────────────┴──────────────▼──────────────┐
                         │              BACKEND  (FastAPI)              │
                         │  /predict  /recommend  /divert  /stream      │
                         └──┬─────────┬─────────┬─────────┬─────────┬───┘
            ┌───────────────┘         │         │         │         └───────────────┐
   ┌────────▼────────┐   ┌────────────▼───┐ ┌───▼────────┐ ┌──▼──────────┐ ┌────────▼─────┐
   │ IMPACT MODEL    │   │ ROUTING ENGINE │ │ RULE ENGINE│ │ ENRICHMENT  │ │ STREAM SIM   │
   │ XGBoost: dur.,  │   │ OSMnx + OSRM   │ │ severity→  │ │ Weather,    │ │ CSV replay + │
   │ closure, prio.  │   │ diversion path │ │ manpower/  │ │ events cal. │ │ live traffic │
   │ → Impact Score  │   │                │ │ barricades │ │             │ │ poller       │
   └────────┬────────┘   └────────────────┘ └────────────┘ └─────────────┘ └──────┬───────┘
            │                                                                       │
   ┌────────▼───────────────────────────────────────────────────────────────────▼────────┐
   │ DATA LAYER:  Astram (historical) · TomTom/Google Traffic · OSM graph · OpenWeather    │
   │              · Events calendar · SQLite/Postgres feature store                         │
   └───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack (decided)

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.11** | Already installed; data + ML + routing all in one ecosystem |
| Modeling | **XGBoost / scikit-learn** | Tabular, fast to train, interpretable (SHAP) |
| Backend | **FastAPI + Uvicorn** | Async, auto Swagger docs, WebSocket for "real-time" |
| Road network | **OSMnx + NetworkX** (local, no server) | Free Bengaluru road graph + diversion routing; no hosted OSRM needed |
| Frontend | **React + Leaflet** (Vite) | Polished map demo for the video; OSM tiles free |
| Fast-track fallback | **Streamlit** | If time-constrained, one-file dashboard in hours |
| Live traffic | **TomTom Traffic API** (free tier, **no credit card**, 2.5k req/day) | Real speed/flow at event coords → real impact + real-time |
| Weather | **Open-Meteo** (free, **no API key, no signup**) | Historical + forecast; zero-friction |
| Storage | **SQLite** (file-based) | Free, no server, ships in repo |
| Deploy | **Hugging Face Spaces** (Streamlit) **or** Render free + Vercel free (**no card**) | Free live Demo Link for submission |

> **Time-box decision:** If by Phase 4 the React frontend is at risk, ship the **Streamlit** version (deploy free on **Hugging Face Spaces** — no credit card). The backend/model/routing stay identical; only the UI changes.

---

## 3. Gap → Implementation Map (all 10 closed)

| Gap | How it gets filled | Module |
|---|---|---|
| **G1** No impact metric | Define **Impact Score** = f(predicted duration band, road-closure prob, priority, corridor weight). **Primary validation = self-contained** (corridor weight derived from in-dataset event density, so it costs nothing). **Optional** cross-check against TomTom free-tier delay for a small sample | Impact Model + Enrichment |
| **G2** No real-time | **CSV replay streamer** (emits events by timestamp — fully free) + **optional** live TomTom free-tier poll at demo time; WebSocket pushes to dashboard | Stream Sim |
| **G3** No road network | **OSMnx** pulls Bengaluru drivable graph; remove affected edge(s); **shortest-path reroute** = diversion plan; render on map | Routing Engine |
| **G4** No optimal-response labels | **Rule engine**: severity tier → (officers, barricades, diversion flag); designed RL-ready (reward = clearance time ↓) | Rule Engine |
| **G5** Sparse planned events | **Class weighting + SMOTE**; augment with scraped **events calendar** (festivals, cricket, BookMyShow) | Model + Enrichment |
| **G6** No external context | Join **Open-Meteo** (free, no key — rain → water-logging risk) + events calendar by date/location | Enrichment |
| **G7** Timezone artifact | Correct UTC↔IST offset (validate vs `created_date`), then enable hour/day features | Data Layer (cleaning) |
| **G8** Missingness | Impute `veh_type`/`zone` via location lookup; drop 100%-empty cols; model on reliable core | Data Layer |
| **G9** Kannada/PII text | **IndicBERT / multilingual-MiniLM** embeddings for `description` as optional feature; keep redaction masks | Model (NLP) |
| **G10** Short history | Document as future work; build retraining pipeline so new data flows in continuously | MLOps |

---

## 4. Phased Build Plan

### Phase 0 — Setup (0.5 day)
- Repo scaffold (`/data /etl /models /api /routing /rules /frontend /notebooks`).
- Env: `pandas, scikit-learn, xgboost, osmnx, networkx, fastapi, uvicorn, requests, imbalanced-learn, shap`.
- Move Astram CSV into `/data/raw`; commit `eda.py`, `charts.py`, reports.
- **Deliverable:** runnable skeleton, README stub.

### Phase 1 — Data foundation (1 day) → fills G7, G8
1. **Cleaning pipeline** (`etl/clean.py`): normalize NULL/empty, fix timezone (G7), drop empty cols, type-cast lat/lon/timestamps.
2. **Imputation** (G8): fill `veh_type`/`zone` via nearest-event/location lookup; flag-impute the rest.
3. **Feature engineering** (`etl/features.py`): cause, event_type, corridor, priority, police_station, lat/lon, hour, dow, month, is_weekend, distance-to-CBD, corridor_event_density.
4. **Target labels**: `duration_minutes` (where available), `road_closure` (binary), `priority` (binary).
- **Deliverable:** clean feature table in SQLite + data-quality summary.

### Phase 2 — Enrichment & external data (1 day) → fills G1(partial), G5, G6 — **all free**
1. **Corridor-weight derivation** (`etl/corridor_weight.py`): compute each corridor's historical event density/severity *from the Astram data itself* → free impact-weighting signal (no external call).
2. **Weather join** (`etl/weather.py`): **Open-Meteo** historical archive by date/grid — no key, no cost (G6).
3. **Events calendar scrape** (`etl/events_cal.py`): public festival/cricket/venue listings → augment planned-event rows (G5).
4. **Optional** TomTom free-tier delay fetch (`etl/traffic.py`) on a ≤300-event sample → cross-validate the Impact Score. Skippable with zero functionality loss.
- **Deliverable:** enriched dataset; correlation chart (Impact Score vs corridor severity, and optionally vs TomTom delay).

### Phase 3 — Models (1.5 days) → fills G1, G5, G9
1. **Three predictors** (`models/train.py`, XGBoost):
   - Duration band (multiclass: <1h / 1–6h / 6–24h / >24h)
   - Road-closure probability (binary)
   - Priority (binary)
2. **Imbalance handling** (G5): class weights + SMOTE on rare causes.
3. **Optional NLP** (G9): IndicBERT embedding of `description` as extra features (ablate to show lift).
4. **Impact Score** (G1): combine the three model outputs + corridor weight into 0–100; **validate** against Phase-2 real delay.
5. **Explainability**: SHAP plots (why this event scores high).
- **Deliverable:** serialized models + metrics report (F1, MAE, calibration) + SHAP figures.

### Phase 4 — Routing & rules (1 day) → fills G3, G4
1. **Routing** (`routing/divert.py`): load Bengaluru OSM graph once (cached GraphML); function `divert(lat,lon,radius)` → removes affected edges, returns alternate polyline + extra distance/time (G3).
2. **Rule engine** (`rules/recommend.py`): map (Impact Score, road_closure, event_type) → `{officers:int, barricades:int, divert:bool, advisory:str}`; tunable thresholds; RL-ready reward stub (G4).
- **Deliverable:** `/divert` and `/recommend` returning real plans.

### Phase 5 — Backend API & real-time (1 day) → fills G2
1. **FastAPI** endpoints: `/predict`, `/recommend`, `/divert`, `/event` (intake), `/stream` (WebSocket).
2. **Stream simulator** (`stream/replay.py`): replays Astram by timestamp at chosen speed; **live TomTom poller** for genuine real-time signal (G2).
- **Deliverable:** documented API (Swagger) + working WebSocket stream.

### Phase 6 — Frontend dashboard (1.5 days)
1. **Map** (Leaflet + OSM): event-density heatmap, live event markers colored by Impact Score, corridor overlay.
2. **Event simulator panel**: enter a new/planned event → instant Impact Score + recommendation + diversion drawn on map.
3. **Live feed panel**: streamed events updating in real time.
4. **Insights tab**: embed the EDA charts.
- **Deliverable:** deployed dashboard (Vercel) → the **Demo Link**.

### Phase 7 — Package & submit (0.5 day)
- Pitch deck (problem → gaps → solution → architecture → demo → impact).
- Record **demo video** (event simulator + live stream + diversion routing).
- README "Instructions to Run"; zip source; push repo.
- **Deliverable:** every required submission field filled.

**Total: ~8 working days** (compressible to ~4–5 with the Streamlit fallback + smaller traffic sample).

---

## 5. Repository Structure

```
saarthi/
├── data/{raw,processed,external}/
├── etl/        clean.py  features.py  traffic.py  weather.py  events_cal.py
├── models/     train.py  impact_score.py  nlp_features.py  artifacts/
├── routing/    divert.py  graph_cache/
├── rules/      recommend.py  config.yaml
├── stream/     replay.py  live_poller.py
├── api/        main.py  schemas.py
├── frontend/   (React+Vite+Leaflet)   OR   app_streamlit.py
├── notebooks/  eda.ipynb
├── reports/    ANALYSIS_REPORT.md  DATASET_GAPS_REPORT.md  charts.py
├── requirements.txt   README.md   docker-compose.yml
```

---

## 6. Submission Deliverable Mapping

| Round-2 field | Produced by |
|---|---|
| Title / Description / Theme | Phase 7 |
| Snapshots | Dashboard screenshots (Phase 6) |
| Video URL | Demo recording (Phase 7) |
| Presentation | Pitch deck (Phase 7) |
| Demo Link | Deployed dashboard (Phase 6) |
| Repository URL | GitHub `saarthi` |
| Source Code | Repo zip (Phase 7) |
| Instructions to Run | README (Phase 0 → 7) |

---

## 7. Risk & Fallback Register

| Risk | Mitigation / Fallback |
|---|---|
| Traffic API quota/cost (G1/G2) | **Optional** only; primary path is dataset-derived + free replay. If used: TomTom free tier (no card), ≤300 events, cached |
| OSM graph load slow (G3) | Pre-download Bengaluru GraphML once, cache to disk |
| React frontend overruns (Phase 6) | Switch to **Streamlit** — same backend, UI in hours |
| NLP adds little (G9) | Keep it optional/ablation; core model unaffected |
| Calendar scrape blocked (G5) | Fall back to SMOTE + class weights only |
| Deploy issues | Demo locally + recorded video as backup |

---

## 7b. Zero-Cost Guarantee 💰

Every component is **free, and no credit card is ever required.**

| Need | Free tool | Cost | Card needed? |
|---|---|---|---|
| Data analysis / ML | pandas, scikit-learn, XGBoost | ₹0 | No |
| Road graph + diversions | OSMnx + NetworkX (runs locally) | ₹0 | No |
| Map tiles | OpenStreetMap via Leaflet | ₹0 | No |
| Weather context | **Open-Meteo** (no signup, no key) | ₹0 | No |
| Real-time traffic (optional) | TomTom free tier (2.5k req/day) | ₹0 | **No** |
| NLP (optional) | HuggingFace transformers (local) | ₹0 | No |
| Backend | FastAPI (self-hosted/local) | ₹0 | No |
| Frontend | React+Vite **or** Streamlit | ₹0 | No |
| Database | SQLite (file in repo) | ₹0 | No |
| Hosting / Demo Link | **Hugging Face Spaces** (Streamlit) | ₹0 | **No** |
| Code hosting | GitHub public repo | ₹0 | No |
| Events calendar | Public web scrape | ₹0 | No |

**Rule:** anything that *could* cost money (Google Maps API, paid traffic feeds, paid cloud) is **excluded or marked optional with a free fallback**. The full prototype — all 10 gaps closed — runs end-to-end on free tools alone. The only "costs" are your time and a free GitHub/Hugging Face login.

**No-API-key path (absolute zero friction):** dataset-derived Impact Score + CSV replay for real-time + OSMnx routing + Open-Meteo + Streamlit on HF Spaces. Closes every gap without registering for a single paid-capable service.

---

## 8. Definition of Done (all gaps closed)

- [ ] G1 Impact Score defined **and** validated against real delay
- [ ] G2 Live stream demo + one real-time traffic source wired
- [ ] G3 Diversion route computed and drawn on map
- [ ] G4 Rule engine returns manpower/barricade plan
- [ ] G5 Rare-class handling + calendar augmentation in training
- [ ] G6 Weather joined into features
- [ ] G7 Timezone corrected, temporal features enabled
- [ ] G8 Imputation done, empty cols dropped
- [ ] G9 Multilingual text feature (or documented ablation)
- [ ] G10 Retraining pipeline + future-work note
- [ ] All 8 submission fields filled

---

*Next action recommendation: start **Phase 0 + Phase 1** (scaffold + clean/feature pipeline) — they unblock everything else and are pure-Python with no external dependencies.*
