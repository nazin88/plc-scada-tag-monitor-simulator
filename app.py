import time
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.config import DEFAULT_TAGS, DEFAULT_ALARMS, SAMPLE_RATE_HZ
from src.db import init_db, write_historian_batch, read_latest_samples, read_trend_window, export_csv_range
from src.simulator import TagSimulator
from src.alarm_engine import AlarmEngine
from src.metrics import compute_kpis

st.set_page_config(page_title="PLC + SCADA Tag Monitor Simulator", layout="wide")

# ---------- Session State ----------
if "sim" not in st.session_state:
    st.session_state.sim = TagSimulator(DEFAULT_TAGS, sample_rate_hz=SAMPLE_RATE_HZ)
if "alarm_engine" not in st.session_state:
    st.session_state.alarm_engine = AlarmEngine(DEFAULT_ALARMS)
if "running" not in st.session_state:
    st.session_state.running = False
if "last_tick" not in st.session_state:
    st.session_state.last_tick = 0.0
if "tick_count" not in st.session_state:
    st.session_state.tick_count = 0

# ---------- DB ----------
init_db()

# ---------- Header ----------
st.title("PLC + SCADA HMI Tag Monitor Simulator")
st.caption("Live tag table • Historian logging (SQLite) • Alarm engine (ACK/Shelve) • Trends • KPI dashboard")

# ---------- Controls ----------
c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
with c1:
    if st.button("▶ Start", use_container_width=True):
        st.session_state.running = True
with c2:
    if st.button("⏸ Pause", use_container_width=True):
        st.session_state.running = False
with c3:
    if st.button("⟲ Reset", use_container_width=True):
        st.session_state.sim.reset()
        st.session_state.alarm_engine.reset()
        st.session_state.tick_count = 0
with c4:
    auto = st.toggle("Auto-refresh", value=True)
with c5:
    st.write(f"Status: **{'RUNNING' if st.session_state.running else 'PAUSED'}**")

# Auto refresh loop (UI)
if auto:
    st_autorefresh(interval=1000, key="refresh")  # 1s

# ---------- Run one tick per render (safe for Streamlit) ----------
def do_tick():
    now = time.time()
    # protect against multiple ticks in same second due to UI events
    if now - st.session_state.last_tick < (1.0 / SAMPLE_RATE_HZ) * 0.8:
        return

    st.session_state.last_tick = now
    ts = datetime.now(timezone.utc)

    # simulate tags
    tag_snapshot = st.session_state.sim.step(ts)

    # alarm evaluation
    alarm_events, active_alarms = st.session_state.alarm_engine.evaluate(ts, tag_snapshot)

    # historian write (tags + alarms)
    write_historian_batch(ts, tag_snapshot, alarm_events)

    st.session_state.tick_count += 1

if st.session_state.running:
    do_tick()

# ---------- Layout ----------
left, right = st.columns([1.05, 0.95])

# ---------- Latest snapshot ----------
latest = read_latest_samples(limit=1)
if latest.empty:
    st.info("No historian data yet. Click **Start** to begin sampling.")
    st.stop()

latest_ts = pd.to_datetime(latest["ts_utc"].iloc[0], utc=True)
latest_tags = st.session_state.sim.last_snapshot  # dict: tag->value

# ---------- KPI Row ----------
kpis = compute_kpis(
    latest_ts=latest_ts,
    tag_snapshot=latest_tags,
    active_alarms=st.session_state.alarm_engine.get_active()
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Active Alarms", kpis["active_alarms"])
k2.metric("Comms Health", kpis["comms_health"])
k3.metric("Line Speed (fpm)", f'{kpis["line_speed"]:.1f}')
k4.metric("Tank Level (%)", f'{kpis["tank_level"]:.1f}')
k5.metric("Samples Logged", st.session_state.tick_count)

# ---------- Left: Tag Monitor + Alarm Console ----------
with left:
    st.subheader("Live Tag Monitor")

    tag_df = pd.DataFrame(
        [{"tag": k, "value": v, "quality": "GOOD"} for k, v in sorted(latest_tags.items())]
    )
    st.dataframe(tag_df, use_container_width=True, hide_index=True)

    st.subheader("Alarm Console")

    active = st.session_state.alarm_engine.get_active_df()
    if active.empty:
        st.success("No active alarms.")
    else:
        st.dataframe(active, use_container_width=True, hide_index=True)

        ac1, ac2, ac3 = st.columns([1, 1, 2])
        with ac1:
            ack_id = st.text_input("ACK Alarm ID", placeholder="e.g., ALM_101", label_visibility="collapsed")
            if st.button("✅ ACK", use_container_width=True):
                st.session_state.alarm_engine.ack(ack_id)
        with ac2:
            shelve_id = st.text_input("Shelve Alarm ID", placeholder="e.g., ALM_101", label_visibility="collapsed")
            if st.button("🕒 Shelve 5m", use_container_width=True):
                st.session_state.alarm_engine.shelve(shelve_id, minutes=5)
        with ac3:
            if st.button("🔕 Silence All (Shelve 2m)", use_container_width=True):
                for _id in st.session_state.alarm_engine.get_active_ids():
                    st.session_state.alarm_engine.shelve(_id, minutes=2)

# ---------- Right: Trends + Reports ----------
with right:
    st.subheader("Trends (Last 10 minutes)")

    tags_to_plot = st.multiselect(
        "Select tags to trend",
        options=list(sorted(latest_tags.keys())),
        default=["LineSpeed_fpm", "TankLevel_pct", "MotorCurrent_A"]
    )

    trend = read_trend_window(minutes=10, tags=tags_to_plot)
    if trend.empty:
        st.warning("Not enough data yet for trends.")
    else:
        # pivot to wide format for plotting
        trend["ts_utc"] = pd.to_datetime(trend["ts_utc"], utc=True)
        wide = trend.pivot_table(index="ts_utc", columns="tag", values="value", aggfunc="last").sort_index()

        st.line_chart(wide)

    st.subheader("Reports / Export")
    rc1, rc2 = st.columns(2)
    with rc1:
        mins = st.number_input("Export range (minutes)", min_value=1, max_value=1440, value=30)
    with rc2:
        if st.button("⬇ Export CSV (Tags + Alarms)", use_container_width=True):
            path = export_csv_range(minutes=int(mins))
            st.success(f"Exported: {path}")

    st.caption("Historian DB: data/historian.db (auto-created). Exports saved in data/exports/")

st.divider()
st.caption("Tip: Pin this repo + add screenshots in the README for maximum recruiter impact.")
