# Dataset Gap & Limitations Report
### Flipkart Hackathon, Round 2 · Event-Driven Congestion · `Astram event data_anonymized`

**Purpose:** This report documents — explicitly and with evidence — **what the dataset does *not* contain** relative to the problem statement, why each gap matters, and how the prototype works around it. Naming these limits honestly is a deliberate scoring strategy: judges reward teams that engineer around their data's boundaries rather than overclaim.

**Dataset:** 8,173 events · 46 columns · 9 Nov 2023 → 8 Apr 2024 · Bengaluru.
**Problem statement:** *"How can historical and real-time data be used to forecast event-related traffic impact and recommend optimal manpower, barricading, and diversion plans?"*

---

## 1. The Core Mismatch in One Sentence

> The problem asks us to **forecast traffic impact in real time and prescribe optimal response plans** — but the dataset is a **historical incident log that never measures traffic, never streams live, and never records what response was taken or whether it worked.**

Everything below is a consequence of that mismatch.

---

## 2. Gap Register (ranked by severity)

| # | What's missing | Severity | Statement requirement it blocks |
|---|---|---|---|
| G1 | No traffic-impact measurement | 🔴 Critical | "forecast traffic impact" |
| G2 | No real-time / streaming data | 🔴 Critical | "real-time data" |
| G3 | No road-network / routing topology | 🔴 Critical | "diversion plans" |
| G4 | No response/outcome labels | 🟠 High | "optimal manpower, barricading" |
| G5 | Sparse planned-event signal | 🟠 High | "event-related" forecasting |
| G6 | No external context (weather, crowd, demand) | 🟡 Medium | impact accuracy |
| G7 | Unreliable temporal field (TZ artifact) | 🟡 Medium | time-of-day forecasting |
| G8 | Heavy missingness on rich fields | 🟡 Medium | feature richness |
| G9 | Multilingual / PII-redacted free text | 🟢 Low | NLP on descriptions |
| G10 | Short, single-window history | 🟢 Low | seasonality/trend modeling |

---

## 3. Detailed Gap Analysis

### 🔴 G1 — No measurement of traffic impact (the biggest gap)
**What exists:** event occurrence, location, cause, and resolution timestamps.
**What's missing:** any quantity describing the *traffic effect* — vehicle volume, average speed, queue/backlog length, delay-minutes, or a congestion index.
**Why it matters:** the statement's central verb is "**forecast traffic impact**." Without a measured impact, there is no ground-truth target to forecast.
**Evidence:** none of the 46 columns encode flow/speed/delay; the closest available signal is event **duration**, computable on only **3,061 / 8,173 rows (37%)**.
**Consequence:** "impact" must be **defined as a proxy** — a composite of *predicted duration band + road-closure probability + priority*. A 25-hour pothole repair on a side lane and a 30-min breakdown on the ORR are *not* distinguishable by true congestion in this data.
**Mitigation:** state the proxy explicitly; optionally weight by corridor importance to approximate real disruption.

### 🔴 G2 — No real-time / streaming data
**What exists:** a static CSV ending 8 Apr 2024.
**What's missing:** any live feed, API, or streaming source.
**Why it matters:** the statement explicitly requires "**real-time data**."
**Consequence:** "real-time" can only be **simulated** — a user enters a new/forthcoming event and the model responds instantly.
**Mitigation:** build a real-time-*ready* architecture (event intake → model → recommendation) and demo it with simulated live input; document where a live feed would plug in.

### 🔴 G3 — No road-network topology → diversions are not computable
**What exists:** point coordinates (`latitude`/`longitude`) and free-text `address`.
**What's missing:** road graph — connectivity, alternate routes, lane/capacity, direction of flow.
**Why it matters:** "recommend... **diversion plans**" requires knowing which roads connect and where traffic can be rerouted.
**Evidence:** `route_path` is **98.3% null**, `direction` **99.5% null**, `end_address` **91.6% null**, `endlatitude`/`endlongitude` mostly `0`.
**Consequence:** diversion routing **cannot** be produced from Astram data alone.
**Mitigation:** integrate an external network (OpenStreetMap / Google Directions) keyed on the event coordinates; Astram supplies the *where*, the map supplies the *reroute*.

### 🟠 G4 — No response or outcome labels
**What exists:** whether a road *was* closed (`requires_road_closure`).
**What's missing:** how many officers/barricades were deployed, the response time, and whether the response was *adequate* or *optimal*.
**Why it matters:** "recommend **optimal** manpower, barricading" implies a notion of optimality to learn from.
**Evidence:** `assigned_to_police_id` **98.4% null**; no manpower-count, no barricade-count, no satisfaction/outcome field.
**Consequence:** manpower/barricade recommendations cannot be *supervised-learned*; there is no labeled "optimal."
**Mitigation:** drive recommendations from a **rule engine** mapping predicted severity → response tier (e.g., High severity + closure → N officers + barricade + diversion). Frame as expert-rules informed by the model, not a learned optimum.

### 🟠 G5 — The planned-event signal is sparse
**What exists:** 467 planned events (6%) and a long tail of event causes.
**What's missing:** volume in exactly the categories the statement cares about.
**Evidence:** `public_event` (84) + `procession` (72) + `vip_movement` (20) + `protest` (15) = **191 rows (2.3%)**. The dataset is **60% `vehicle_breakdown`**.
**Why it matters:** model accuracy on rare classes is inherently weaker; per-event-type forecasting has little data for the marquee use case.
**Consequence:** a festival/rally-specific forecaster would be under-powered.
**Mitigation:** target **all congestion-causing events**, treating planned events as the highest-severity class; use class weighting and report confidence honestly.

### 🟡 G6 — No external context
**Missing:** weather, crowd-size estimates, baseline traffic demand, public-holiday calendar, event scale (attendance).
**Why it matters:** real event impact scales with crowd size and weather (e.g., water-logging severity).
**Mitigation:** optionally enrich with a weather API and holiday calendar by date+location.

### 🟡 G7 — Unreliable temporal field (timezone artifact)
**Observation:** raw `start_datetime` hour distribution peaks at **2–3 AM IST** and is near-empty in the evening — inconsistent with real traffic.
**Likely cause:** UTC/IST storage mislabeling.
**Why it matters:** "time of day" is a natural forecasting feature but is currently **untrustworthy**.
**Mitigation:** validate against `created_date`, correct the offset, or drop hour-of-day features until verified.

### 🟡 G8 — Heavy missingness on the descriptive fields
**Evidence (% null):** `end_datetime` 94, `route_path` 98.3, `junction` 69.3, `zone` 57.9, `gba_identifier` 57.9, `veh_type`/`veh_no` 40.2, `description` 16.6; **100% empty:** `map_file`, `comment`, `meta_data`.
**Consequence:** several intuitively useful features are too sparse to rely on; duration (which needs an end timestamp) is limited to 37% of rows.
**Mitigation:** model on the reliable core (cause, location, corridor, type, priority, police_station); impute or treat sparse fields as optional.

### 🟢 G9 — Multilingual, PII-redacted free text
**Observation:** `description` mixes **Kannada and English** and contains `[PERSON]`/`[LOCATION]` redactions.
**Consequence:** NLP on descriptions needs multilingual handling and tolerance for masked tokens.
**Mitigation:** treat description as a low-priority enrichment; use multilingual embeddings if used at all.

### 🟢 G10 — Short, single-window history
**Observation:** only ~5 months (Nov 2023–Apr 2024).
**Consequence:** no full-year seasonality (monsoon, major festival calendar) can be learned; trend extrapolation is weak.
**Mitigation:** scope claims to within-period patterns; note that more history would improve seasonality.

---

## 4. Requirement Coverage Scorecard

| Problem-statement requirement | Dataset can support it? | Gap(s) | Workaround |
|---|---|---|---|
| Forecast traffic **impact** | ⚠️ Proxy only | G1 | Duration + closure + priority composite |
| Quantify impact **in advance** | ✅ Yes | — | Predict from cause/location/type |
| **Real-time** data | ❌ No | G2 | Simulated live intake; RT-ready design |
| Recommend **manpower** | ⚠️ Heuristic | G4 | Severity → rule-based tiers |
| Recommend **barricading** | ✅ Yes | — | `requires_road_closure` is a clean target |
| Recommend **diversions** | ❌ No (native) | G3 | External road network (OSM/Google) |
| **Post-event learning** | ✅ Yes | — | 8,173 historical records as training set |

**Net:** of the statement's core deliverables, **2 are directly supported, 2 need proxies/heuristics, and 2 require external integration.**

---

## 5. Recommendations Summary

1. **Reframe "impact" as an explicit proxy** and say so in the deck.
2. **Build real-time-ready, demo with simulation** — don't claim a live feed you don't have.
3. **Integrate an external road network** for the diversion feature; Astram provides location, the map provides routing.
4. **Use a rule engine for manpower/barricades**, informed by the severity model, since no optimal labels exist.
5. **Target all event types**, planned events as the top severity class.
6. **Fix or drop the timezone-affected hour field** before using temporal features.
7. **Model on the reliable core columns**; treat sparse fields as optional enrichment.

> **One-line pitch posture:** *"The Astram data tells us reliably where and how severe disruptions are; we engineer around its three gaps — no impact metric, no live feed, no road graph — with a proxy target, a simulated/RT-ready pipeline, and an external routing layer."*

---

*Companion documents: `ANALYSIS_REPORT.md` (full EDA), `eda.py`, `charts.py`, `report_assets/`. Missingness figure: `report_assets/07_missing.png`.*
