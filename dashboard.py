
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "mqtt_insight.db"

st.set_page_config(
    page_title="MQTT Insight",
    page_icon="📡",
    layout="wide",
)

st.title("📡 MQTT Insight")
st.caption("IoT telemetry monitoring and sensor analytics")

with st.sidebar:
    st.header("Dashboard settings")
    refresh_seconds = st.selectbox(
        "Refresh interval",
        [2, 5, 10, 30],
        index=1,
        format_func=lambda seconds: f"{seconds} seconds",
    )
    rows_to_show = st.selectbox(
        "Recent readings",
        [50, 100, 250, 500],
        index=1,
    )
    stale_seconds = st.selectbox(
    "Device stale timeout",
    [10, 15, 30, 60],
    index=1,
    format_func=lambda seconds: f"{seconds} seconds",
)


@st.cache_data(ttl=2)
def load_alerts():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        return pd.read_sql_query(
            """
            SELECT device_id, alert_type, severity, metric,
                   value, message, created_at
            FROM alerts
            ORDER BY id DESC
            LIMIT 200
            """,
            connection,
        )


def get_device_status(data, stale_seconds):
    if data.empty:
        return pd.DataFrame()

    latest_by_device = (
        data.sort_values("received_at")
        .groupby("device_id", as_index=False)
        .tail(1)
        .copy()
    )

    now = pd.Timestamp.now(tz="UTC")
    latest_by_device["seconds_since_last_seen"] = (
        now - latest_by_device["received_at"]
    ).dt.total_seconds()

    latest_by_device["status"] = latest_by_device[
        "seconds_since_last_seen"
    ].apply(
        lambda seconds: "STALE" if seconds > stale_seconds else "ONLINE"
    )

    return latest_by_device[
        [
            "device_id",
            "received_at",
            "seconds_since_last_seen",
            "status",
        ]
    ].sort_values("device_id")

@st.cache_data(ttl=2)
def load_telemetry():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        return pd.read_sql_query(
            """
            SELECT id, device_id, topic, temperature_c,
                   humidity_pct, sensor_timestamp, received_at
            FROM telemetry
            ORDER BY id DESC
            LIMIT 5000
            """,
            connection,
        )


if st.button("Refresh now"):
    st.cache_data.clear()

df = load_telemetry()

if df.empty:
    st.info(
        "No telemetry records found yet. Start Mosquitto, "
        "the MQTT processor, and the sensor publisher."
    )
    st.stop()

df["received_at"] = pd.to_datetime(
    df["received_at"], errors="coerce", utc=True
)
df = df.dropna(subset=["received_at"]).sort_values("received_at")

latest = df.iloc[-1]
device_count = df["device_id"].nunique()
message_count = len(df)

# Latest received record and overall database statistics
metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "Latest temperature",
    f"{latest['temperature_c']:.1f} °C",
)
metric2.metric(
    "Latest humidity",
    f"{latest['humidity_pct']:.1f}%",
)
metric3.metric("Devices detected", device_count)
metric4.metric("Loaded readings", message_count)

st.divider()

# Device filter
devices = sorted(df["device_id"].dropna().unique().tolist())
selected_devices = st.multiselect(
    "Filter by device",
    options=devices,
    default=devices,
)

filtered = df[df["device_id"].isin(selected_devices)].copy()

if filtered.empty:
    st.warning("Select at least one device to view its telemetry.")
    st.stop()

st.subheader("Telemetry trends")

chart_data = (
    filtered.set_index("received_at")[
        ["temperature_c", "humidity_pct"]
    ]
    .rename(
        columns={
            "temperature_c": "Temperature (°C)",
            "humidity_pct": "Humidity (%)",
        }
    )
)

left, right = st.columns(2)

with left:
    st.markdown("**Temperature over time**")
    st.line_chart(chart_data[["Temperature (°C)"]])

with right:
    st.markdown("**Humidity over time**")
    st.line_chart(chart_data[["Humidity (%)"]])


st.divider()
st.subheader("Device health")

device_status = get_device_status(df, stale_seconds)

if device_status.empty:
    st.info("No devices have reported telemetry yet.")
else:
    online_count = int((device_status["status"] == "ONLINE").sum())
    stale_count = int((device_status["status"] == "STALE").sum())

    health1, health2 = st.columns(2)
    health1.metric("Online devices", online_count)
    health2.metric("Stale devices", stale_count)

    st.dataframe(
        device_status,
        use_container_width=True,
        hide_index=True,
        column_config={
            "received_at": st.column_config.DatetimeColumn(
                "Last received (UTC)",
                format="YYYY-MM-DD HH:mm:ss",
            ),
            "seconds_since_last_seen": st.column_config.NumberColumn(
                "Seconds since last seen",
                format="%.1f s",
            ),
        },
    )

st.divider()
st.subheader("Alert history")

alerts_df = load_alerts()

if alerts_df.empty:
    st.success("No alerts recorded yet.")
else:
    critical_count = int(
        (alerts_df["severity"] == "critical").sum()
    )
    warning_count = int(
        (alerts_df["severity"] == "warning").sum()
    )

    alert1, alert2 = st.columns(2)
    alert1.metric("Critical alerts", critical_count)
    alert2.metric("Warnings", warning_count)

    st.dataframe(
        alerts_df,
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Latest readings")

recent = filtered.sort_values(
    "received_at", ascending=False
).head(rows_to_show).copy()

recent["received_at"] = recent["received_at"].dt.strftime(
    "%Y-%m-%d %H:%M:%S UTC"
)

st.dataframe(
    recent[
        [
            "received_at",
            "device_id",
            "temperature_c",
            "humidity_pct",
            "topic",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Displaying {len(recent)} recent readings from "
    f"{device_count} detected devices in the loaded dataset."
)

# Optional automatic refresh
try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(
        interval=refresh_seconds * 1000,
        key="mqtt_insight_refresh",
    )
except ImportError:
    st.caption(
        "Automatic refresh is not installed. Use Refresh now "
        "or install streamlit-autorefresh."
    )
