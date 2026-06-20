"""
Saarthi — Phase 4: resource recommendation rule engine (G4).
Maps a scored event -> manpower, barricades, diversion, advisory.
No 'optimal' labels exist in the data, so this is an expert rule engine,
designed RL-ready (reward = clearance-time reduction) for future learning.
"""

# base manpower by severity tier
_BASE = {"Critical": 12, "High": 7, "Moderate": 4, "Low": 2}
# multiplier by event type
_TYPE_MULT = {"planned": 1.4, "unplanned": 1.0}


def recommend(scored: dict, event: dict) -> dict:
    sev = scored["severity"]
    score = scored["impact_score"]
    p_close = scored["p_road_closure"]
    etype = event.get("event_type", "unplanned")

    officers = round(_BASE[sev] * _TYPE_MULT.get(etype, 1.0))
    # heavy/long events near CBD need more
    if scored["expected_minutes"] >= 720:
        officers += 3
    if event.get("dist_to_cbd_km", 99) < 5:
        officers += 2

    barricade = p_close >= 0.5 or sev in ("Critical", "High")
    n_barricades = (6 if sev == "Critical" else 4 if sev == "High"
                    else 2 if barricade else 0)
    divert = p_close >= 0.5 or sev == "Critical"

    tow = event.get("event_cause") in ("vehicle_breakdown", "accident")
    drainage = event.get("event_cause") == "water_logging"

    advisory = _advisory(sev, divert, etype)
    eta_clear = scored["expected_minutes"]

    return {
        "officers": int(officers),
        "barricades": int(n_barricades),
        "deploy_barricade": bool(barricade),
        "recommend_diversion": bool(divert),
        "tow_truck": bool(tow),
        "drainage_crew": bool(drainage),
        "advisory": advisory,
        "expected_clearance_min": int(eta_clear),
        "priority_tier": sev,
        "confidence": _confidence(score),
    }


def _advisory(sev, divert, etype):
    parts = []
    if sev in ("Critical", "High"):
        parts.append("Pre-position response team before event start"
                     if etype == "planned" else "Dispatch rapid-response unit now")
    if divert:
        parts.append("Activate diversion + issue public traffic advisory")
    if not parts:
        parts.append("Monitor; standard patrol sufficient")
    return ". ".join(parts) + "."


def _confidence(score):
    # crude confidence band for transparency
    return "high" if (score >= 70 or score <= 25) else "medium"


if __name__ == "__main__":
    import json
    s = dict(impact_score=78, severity="Critical", expected_minutes=800,
             p_road_closure=0.8, p_high_priority=0.9, duration_band="6-24h")
    e = dict(event_type="planned", event_cause="procession", dist_to_cbd_km=3)
    print(json.dumps(recommend(s, e), indent=2))
