# Data Analysis Report — Event-Driven Congestion
### Flipkart Hackathon, Round 2 (Prototype) · Bengaluru Traffic

**Dataset:** `Astram event data_anonymized` · **Records:** 8,173 events · **Columns:** 46
**Period:** 9 Nov 2023 → 8 Apr 2024 (≈5 months) · **Geography:** Bengaluru Urban/Rural
**Prepared for:** Problem Statement — *"How can historical and real-time data be used to forecast event-related traffic impact and recommend optimal manpower, barricading, and diversion plans?"*

---

## 1. Executive Summary

The Astram dataset is a high-quality, **100% geocoded** log of 8,173 traffic-disrupting events across Bengaluru over five months. It is rich enough to build a credible **severity-forecasting and resource-targeting engine**, but it has three structural limits that shape the prototype's scope:

1. **It logs incidents, not impact.** Every record says *what happened* and *how long until resolved*, but never quantifies traffic effect (no speed, volume, or delay). Impact must be modeled via a **proxy (event duration + road-closure + priority)**.
2. **It is historical only.** No live feed exists; "real-time" must be **simulated** (new event → instant prediction). The architecture can be real-time-ready.
3. **The "event" signal is sparse.** Planned events (rallies/processions/VIP) are only **~6%** of rows; the dataset is dominated by **vehicle breakdowns (60%)**. The prototype should target *all* congestion-causing events, with planned events as the highest-impact class.

**Verdict:** Strong foundation for *predict-severity + rank-where-to-deploy*. Diversion routing and learned-optimal manpower require **external data** (road network) and **rule-based heuristics** layered on top.

---

## 2. Dataset Overview

| Property | Value |
|---|---|
| Rows | 8,173 |
| Columns | 46 |
| Date range | 2023-11-09 → 2024-04-08 |
| Geocoded rows | 8,173 (100%) |
| Planned / Unplanned | 467 (6%) / 7,706 (94%) |
| Required road closure | 676 (8%) |
| Rows with computable duration | 3,061 (37%) |

**Clean, high-value columns (~0% null):** `id`, `event_type`, `latitude`, `longitude`, `address`, `event_cause`, `requires_road_closure`, `start_datetime`, `status`, `priority`, `police_station`, `corridor`.

---

## 3. Key Findings

### 3.1 Event Causes — incident-dominated
Vehicle breakdowns alone are **60%** of all events. The classic "event" causes named in the problem statement (`public_event`, `procession`, `vip_movement`, `protest`) total only **~191 rows (2.3%)**.

![Event causes](report_assets/01_causes.png)

| Cause | Count | % |
|---|---|---|
| vehicle_breakdown | 4,896 | 59.9% |
| others | 638 | 7.8% |
| pot_holes | 537 | 6.6% |
| construction | 480 | 5.9% |
| water_logging | 458 | 5.6% |
| accident | 365 | 4.5% |
| tree_fall | 284 | 3.5% |
| public_event / procession / vip / protest | 191 | 2.3% |

### 3.2 Planned events are rarer but far more disruptive
Planned events close roads **5.5× more often** and last **~6× longer** than unplanned ones — a clean, learnable severity signal.

![Type and closure](report_assets/02_type_closure.png)

| Type | Count | Road-closure rate | Median duration |
|---|---|---|---|
| Planned | 467 | **36.2%** | **340 min** |
| Unplanned | 7,706 | 6.6% | 53 min |

### 3.3 Resolution time varies 36× by cause → the impact proxy
Median resolution is **57 min** overall, but ranges from 41 min (breakdowns) to ~1,489 min (pothole repairs). This spread is what makes severity *predictable from cause*.

![Duration by cause](report_assets/03_duration.png)

| Cause | Median duration (min) |
|---|---|
| pot_holes | 1,489 |
| water_logging | 790 |
| road_conditions | 774 |
| construction | 717 |
| tree_fall | 215 |
| public_event | 185 |
| others | 110 |
| accident | 42 |
| vehicle_breakdown | 41 |

### 3.4 Strong corridor & geographic concentration → deployment targeting
Events cluster on a handful of arterial corridors and city zones, directly enabling **manpower ranking** by location.

![Corridors](report_assets/04_corridors.png)
![Heatmap](report_assets/05_heatmap.png)

- **Top corridors:** Mysore Road (743), Bellary Road 1 (610), Tumkur Road (458), Bellary Road 2 (379), Hosur Road (298), ORR segments.
- **Top police stations:** Yelahanka (377), HAL Old Airport (361), Sadashivanagar (302), Byatarayanapura (297), Halasuru Gate (297).
- **Spatial hotspots** concentrate around central Bengaluru and ORR (heatmap above).

### 3.5 Temporal trend
Volume is steady-to-rising across the period, peaking in **Mar 2024 (1,929)**. (April is a partial month.)

![Monthly](report_assets/06_monthly.png)

> ⚠️ **Hour-of-day is unreliable.** The raw timestamps peak at 2–3 AM IST, which is inconsistent with real traffic and points to a **UTC/IST storage artifact**. Time-of-day features must be validated/corrected before use.

---

## 4. Data Quality Assessment

![Missingness](report_assets/07_missing.png)

| Tier | Columns | Implication |
|---|---|---|
| ✅ Reliable (<5% null) | event_type, lat/lon, address, event_cause, road_closure, priority, police_station, corridor, status | Core model features |
| ⚠️ Partial (15–60%) | description (17%), veh_type (40%), zone (58%) | Usable with imputation/optional features |
| ❌ Sparse (>60%) | closed_datetime (62%), junction (69%), end_address (92%), end_datetime (94%), route_path (98%), resolved_* (99%), direction (99.5%) | Limited use |
| ⛔ Empty (100%) | map_file, comment, meta_data | Drop |

**Other quality notes:**
- Duration computable on only **3,061 / 8,173** rows (needs a resolved/closed timestamp).
- `description` is mixed **Kannada/English** with `[PERSON]`/`[LOCATION]` PII redactions.
- `requires_road_closure` and several fields contain stray parsing noise in raw text; clean before modeling.

---

## 5. Problem Statement: Expectations vs. Dataset Capability

| Expectation | Supported? | Notes |
|---|---|---|
| **Forecast traffic impact** | ⚠️ Partial | No direct impact metric; use duration + closure + priority as proxy |
| **Quantify impact in advance** | ✅ | Predictable from cause/location/type |
| **Recommend manpower** | ⚠️ Heuristic | No labeled "optimal" response; derive from predicted severity |
| **Recommend barricading** | ✅ | `requires_road_closure` is a clean training target |
| **Recommend diversions** | ❌ | No road-network/topology; needs external map (OSM/Google) |
| **Use real-time data** | ❌ | Static historical CSV; simulate live input |
| **Post-event learning** | ✅ | 8,173 historical records = the training corpus |

---

## 6. What the Dataset Lacks (Critical Gaps)

1. **No true impact metric** — no vehicle counts, speeds, queue lengths, or delay-minutes. Duration is a *resolution-time proxy*, not congestion measurement.
2. **No real-time / streaming data** — analysis is retrospective; live capability must be designed-for, not demonstrated from data.
3. **No road-network topology** — cannot compute diversions from this data alone (`route_path` 98% null, `direction` 99.5% null).
4. **No labeled response outcomes** — `assigned_to_police_id` is 98.4% null; "optimal manpower" cannot be *learned*, only *recommended by rule*.
5. **Sparse event signal** — the planned-event class the statement targets is only 2.3% of rows.
6. **No external context** — no weather, crowd-size, or reliable time-of-day features.

---

## 7. Recommended Prototype Direction

A three-layer **Congestion Impact & Resource Recommendation** system:

1. **Predict** — given event cause, location, corridor, type, vehicle: output expected **duration band**, **road-closure probability**, and **priority**.
2. **Recommend** — rule engine maps predicted severity → **manpower level + barricade flag + diversion flag**.
3. **Visualize** — live **map dashboard** with hotspot heatmap and corridor load (the 100% geocoding makes this demo-strong), plus a "simulate a new event" panel for the real-time story.

**Honest pitch framing for judges:** *"Saarathi forecasts severity from historical Astram data, layers an external road-network for diversions and a rule engine for manpower/barricades, and is architected for real-time feeds — explicitly engineering around the dataset's limits."* Naming the gaps and engineering around them is a scoring advantage.

---

## 8. Reproducibility

| File | Purpose |
|---|---|
| `eda.py` | Full exploratory analysis (distributions, durations, hotspots) |
| `charts.py` | Generates all figures in `report_assets/` |
| `report_assets/*.png` | 7 figures referenced above |
| `ANALYSIS_REPORT.md` | This report |

*All statistics computed with pandas; durations exclude negatives and >1-week outliers; geo filtered to Bengaluru bounding box (12.7–13.3 N, 77.3–77.9 E).*
