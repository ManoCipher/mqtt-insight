
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "mqtt_insight.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                temperature_c REAL NOT NULL,
                humidity_pct REAL NOT NULL,
                sensor_timestamp TEXT,
                received_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_device_received
            ON telemetry (device_id, received_at)
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                telemetry_id INTEGER,
                FOREIGN KEY (telemetry_id) REFERENCES telemetry(id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_created
            ON alerts (created_at DESC)
        """)


def save_telemetry(
    device_id,
    topic,
    temperature_c,
    humidity_pct,
    sensor_timestamp,
    received_at,
):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO telemetry (
                device_id, topic, temperature_c, humidity_pct,
                sensor_timestamp, received_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                topic,
                temperature_c,
                humidity_pct,
                sensor_timestamp,
                received_at,
            ),
        )
        return cursor.lastrowid


def get_recent_telemetry(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM telemetry
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_device_history(device_id, limit=30):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT temperature_c, humidity_pct
            FROM telemetry
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()

    # Return oldest-to-newest for consistent historical processing.
    return [dict(row) for row in reversed(rows)]


def save_alert(
    device_id,
    alert_type,
    severity,
    metric,
    value,
    message,
    created_at,
    telemetry_id=None,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO alerts (
                device_id, alert_type, severity, metric,
                value, message, created_at, telemetry_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                alert_type,
                severity,
                metric,
                value,
                message,
                created_at,
                telemetry_id,
            ),
        )


def get_recent_alerts(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM alerts
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
