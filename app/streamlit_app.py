"""
Saarathi — Event-Driven Congestion intelligence for Bengaluru.
Flipkart Hackathon Round 2 prototype.

Run:  streamlit run app/streamlit_app.py
"""
import os, sys, math
import pandas as pd
import numpy as np
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from models.predict import score_event           # noqa: E402
from rules.recommend import recommend             # noqa: E402
from routing.divert import plan_diversion         # noqa: E402

CBD = (12.9759, 77.6045)
SEV_COLOR = {"Critical": "#e63946", "High": "#f3722c",
             "Moderate": "#f7ca00", "Low": "#43aa8b"}

st.set_page_config(page_title="Saarathi | Bengaluru Traffic Intelligence",
                   layout="wide", page_icon="🚦")


@st.cache_data
def load_scored():
    p = os.path.join(HERE, "data", "processed", "events_scored.csv")
    df = pd.read_csv(p, parse_dates=["start_ist"])
    return df


@st.cache_data
def lookups(df):
    cw = df.groupby("corridor")["corridor_weight"].first().to_dict()
    return {
        "causes": sorted(df.event_cause.dropna().unique().tolist()),
        "corridors": sorted(df.corridor.dropna().unique().tolist()),
        "zones": sorted(df.zone.dropna().unique().tolist()),
        "corridor_weight": cw,
    }


def haversine(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p)
         * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(a))


def build_event(cause, etype, corridor, zone, lat, lon, hour, dow, lk):
    return dict(
        event_type=etype, event_cause=cause, corridor=corridor, zone=zone,
        veh_type="unknown", latitude=lat, longitude=lon, hour=hour, dow=dow,
        is_weekend=int(dow >= 5), month=3,
        dist_to_cbd_km=round(haversine(lat, lon, *CBD), 2),
        has_endpoint=0, corridor_weight=lk["corridor_weight"].get(corridor, 0.01),
    )


df = load_scored()
lk = lookups(df)

st.title("🚦 Saarathi — Event-Driven Congestion Intelligence")
st.caption("Forecast traffic impact of events and recommend manpower, barricading & "
           "diversions — Bengaluru. Flipkart Hackathon R2.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["🗺️ Operations Map", "🎯 Impact Simulator", "📡 Real-Time Stream", "📊 Insights"])

# ---------------------------------------------------------------- TAB 1: MAP
with tab1:
    c1, c2 = st.columns([3, 1])
    with c2:
        st.subheader("Filters")
        sev_sel = st.multiselect("Severity", list(SEV_COLOR),
                                 default=["Critical", "High"])
        cause_sel = st.multiselect("Cause", lk["causes"], default=[])
        max_pts = st.slider("Max markers", 100, 3000, 800, 100)
        show_heat = st.checkbox("Heatmap layer", True)
    d = df.copy()
    if sev_sel:
        d = d[d.severity.isin(sev_sel)]
    if cause_sel:
        d = d[d.event_cause.isin(cause_sel)]
    with c1:
        st.subheader(f"Event hotspots — {len(d):,} events")
        m = folium.Map(location=CBD, zoom_start=11, tiles="cartodbpositron")
        if show_heat:
            HeatMap(d[["latitude", "longitude", "impact_score"]].values.tolist(),
                    radius=9, blur=12, min_opacity=0.3).add_to(m)
        for _, r in d.head(max_pts).iterrows():
            folium.CircleMarker(
                [r.latitude, r.longitude], radius=3,
                color=SEV_COLOR.get(r.severity, "#888"), fill=True, fill_opacity=0.7,
                popup=f"{r.event_cause} | {r.severity} ({r.impact_score})",
            ).add_to(m)
        st_folium(m, height=560, use_container_width=True)
    st.info("**Deployment view:** the redder/denser the area, the higher the predicted "
            "operational load — use it to pre-position manpower across the city.")

# ----------------------------------------------------- TAB 2: IMPACT SIMULATOR
with tab2:
    st.subheader("Forecast a new / upcoming event")
    a, b = st.columns(2)
    with a:
        etype = st.selectbox("Event type", ["planned", "unplanned"])
        cause = st.selectbox("Cause", lk["causes"],
                             index=lk["causes"].index("procession")
                             if "procession" in lk["causes"] else 0)
        corridor = st.selectbox("Corridor", lk["corridors"])
        zone = st.selectbox("Zone", lk["zones"])
    with b:
        hour = st.slider("Hour of day", 0, 23, 18)
        dow = st.selectbox("Day", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                           index=5)
        dow_i = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].index(dow)
        lat = st.number_input("Latitude", value=12.9716, format="%.4f")
        lon = st.number_input("Longitude", value=77.5946, format="%.4f")

    if st.button("⚡ Forecast impact & recommend", type="primary"):
        ev = build_event(cause, etype, corridor, zone, lat, lon, hour, dow_i, lk)
        sc = score_event(ev)
        rec = recommend(sc, ev)
        div = plan_diversion(lat, lon)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Impact Score", f"{sc['impact_score']}/100", sc["severity"])
        k2.metric("Expected duration", f"{sc['expected_minutes']} min")
        k3.metric("Road-closure prob.", f"{sc['p_road_closure']*100:.0f}%")
        k4.metric("Officers to deploy", rec["officers"])

        st.markdown(f"### 🛡️ Recommended response — **{rec['priority_tier']}** "
                    f"({rec['confidence']} confidence)")
        r1, r2 = st.columns(2)
        with r1:
            st.write(f"- **Officers:** {rec['officers']}")
            st.write(f"- **Barricades:** {rec['barricades']} "
                     f"({'deploy' if rec['deploy_barricade'] else 'not needed'})")
            st.write(f"- **Diversion:** {'✅ activate' if rec['recommend_diversion'] else '—'}")
        with r2:
            st.write(f"- **Tow truck:** {'✅' if rec['tow_truck'] else '—'}")
            st.write(f"- **Drainage crew:** {'✅' if rec['drainage_crew'] else '—'}")
            st.write(f"- **Est. clearance:** {rec['expected_clearance_min']} min")
        st.success(f"📋 Advisory: {rec['advisory']}")

        if rec["recommend_diversion"]:
            st.markdown("### 🔀 Suggested diversion")
            dm = folium.Map(location=[lat, lon], zoom_start=15,
                            tiles="cartodbpositron")
            folium.Marker([lat, lon], tooltip="Blocked point",
                          icon=folium.Icon(color="red", icon="ban-circle")).add_to(dm)
            folium.PolyLine(div["route"], color="#2874f0", weight=5,
                            tooltip=f"Detour +{div.get('extra_km','?')} km").add_to(dm)
            st_folium(dm, height=380, use_container_width=True)
            st.caption(f"Diversion mode: {div['mode']} · detour {div['detour_km']} km "
                       f"(+{div.get('extra_min_est','?')} min est.)")

# ------------------------------------------------------- TAB 3: REAL-TIME STREAM
with tab3:
    st.subheader("📡 Real-time event stream (replay)")
    st.caption("Historical events replayed in time order — simulates a live feed. "
               "Architecture accepts a real feed at the same intake point.")
    speed = st.select_slider("Replay window", ["50", "100", "200", "500"], "100")
    if "cursor" not in st.session_state:
        st.session_state.cursor = 0
    cc1, cc2, cc3 = st.columns(3)
    if cc1.button("▶ Advance"):
        st.session_state.cursor += int(speed)
    if cc2.button("⏮ Reset"):
        st.session_state.cursor = 0
    cur = min(st.session_state.cursor, len(df))
    cc3.metric("Events processed", f"{cur:,}/{len(df):,}")

    stream = df.sort_values("start_ist").head(cur)
    live = stream.tail(int(speed))
    sm = folium.Map(location=CBD, zoom_start=11, tiles="cartodbpositron")
    for _, r in live.iterrows():
        folium.CircleMarker([r.latitude, r.longitude], radius=4,
                            color=SEV_COLOR.get(r.severity, "#888"),
                            fill=True, fill_opacity=0.8,
                            popup=f"{r.event_cause} {r.impact_score}").add_to(sm)
    st_folium(sm, height=460, use_container_width=True)
    if len(live):
        st.dataframe(live[["start_ist", "event_cause", "corridor", "severity",
                           "impact_score", "p_road_closure"]].tail(10),
                     use_container_width=True, hide_index=True)

# ------------------------------------------------------------- TAB 4: INSIGHTS
with tab4:
    st.subheader("Dataset insights (8,057 events · Nov 2023–Apr 2024)")
    i1, i2 = st.columns(2)
    with i1:
        st.markdown("**Events by cause**")
        st.bar_chart(df.event_cause.value_counts().head(10))
        st.markdown("**Severity mix (predicted)**")
        st.bar_chart(df.severity.value_counts())
    with i2:
        st.markdown("**Top corridors by event load**")
        st.bar_chart(df[df.corridor != "Non-corridor"]
                     .corridor.value_counts().head(10))
        st.markdown("**Mean impact by event type**")
        st.bar_chart(df.groupby("event_type").impact_score.mean())
    st.caption("Planned events: rarer but higher impact & far higher road-closure rate.")

st.divider()
st.caption("Saarathi · Smart Anticipatory Allocation for Road-traffic Advisory, Triage, Handling & Intervention · "
           "Built on the anonymised Astram dataset. Diversion uses a local engine "
           "(OSM routing plugs in where reachable).")
