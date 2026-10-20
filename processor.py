
import json
from datetime import datetime, timezone
from statistics import median

import paho.mqtt.client as mqtt

from database import (
    get_device_history,
    initialize_database,
    save_alert,
    save_telemetry,
)

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TOPIC = "mqtt-insight/sensors/#"

# Initial demonstration thresholds
TEMP_MIN_C = 10.0
TEMP_MAX_C = 32.0
HUMIDITY_MIN_PCT = 20.0
HUMIDITY_MAX_PCT = 80.0

# Anomaly detection settings
HISTORY_SIZE = 30
MIN_HISTORY_POINTS = 10
MODIFIED_Z_THRESHOLD = 3.5


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def detect_threshold_alerts(device_id, temperature, humidity, timestamp):
    alerts = []

    if temperature < TEMP_MIN_C:
        alerts.append((
            "threshold", "warning", "temperature_c", temperature,
            f"Temperature below {TEMP_MIN_C} °C",
        ))
    elif temperature > TEMP_MAX_C:
        severity = "critical" if temperature > 35.0 else "warning"
        alerts.append((
            "threshold", severity, "temperature_c", temperature,
            f"Temperature above {TEMP_MAX_C} °C",
        ))

    if humidity < HUMIDITY_MIN_PCT:
        alerts.append((
            "threshold", "warning", "humidity_pct", humidity,
            f"Humidity below {HUMIDITY_MIN_PCT}%",
        ))
    elif humidity > HUMIDITY_MAX_PCT:
        alerts.append((
            "threshold", "warning", "humidity_pct", humidity,
            f"Humidity above {HUMIDITY_MAX_PCT}%",
        ))

    for alert_type, severity, metric, value, message in alerts:
        save_alert(
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            metric=metric,
            value=value,
            message=message,
            created_at=timestamp,
        )
        print(f"[ALERT] {severity.upper()} | {device_id} | {message}")


def check_anomaly(device_id, metric, current_value, history, timestamp):
    if len(history) < MIN_HISTORY_POINTS:
        return

    values = [float(row[metric]) for row in history]
    center = median(values)
    deviations = [abs(value - center) for value in values]
    mad = median(deviations)

    # Avoid dividing by zero when historical values are identical.
    if mad == 0:
        return

    modified_z = 0.6745 * (current_value - center) / mad

    if abs(modified_z) >= MODIFIED_Z_THRESHOLD:
        message = (
            f"Unusual {metric} reading: {current_value:.2f}; "
            f"historical median {center:.2f}, "
            f"modified z-score {modified_z:.2f}"
        )

        save_alert(
            device_id=device_id,
            alert_type="anomaly",
            severity="warning",
            metric=metric,
            value=current_value,
            message=message,
            created_at=timestamp,
        )
        print(f"[ANOMALY] {device_id} | {message}")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[ERROR] MQTT connection failed: {reason_code}")
        return

    print(f"[CONNECTED] {BROKER_HOST}:{BROKER_PORT}")
    client.subscribe(TOPIC)
    print(f"[SUBSCRIBED] {TOPIC}")


def on_message(client, userdata, message):
    received_at = utc_now()

    try:
        data = json.loads(message.payload.decode("utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Payload must be a JSON object")

        device_id = data.get("device_id")
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id must be a non-empty string")

        temperature = float(data["temperature_c"])
        humidity = float(data["humidity_pct"])

        if not (-50 <= temperature <= 100):
            raise ValueError("Temperature outside accepted range")

        if not (0 <= humidity <= 100):
            raise ValueError("Humidity must be between 0 and 100")

        device_id = device_id.strip()

        # Read history before inserting this reading so that the current
        # reading is not included in its own anomaly baseline.
        history = get_device_history(device_id, HISTORY_SIZE)

        telemetry_id = save_telemetry(
            device_id=device_id,
            topic=message.topic,
            temperature_c=temperature,
            humidity_pct=humidity,
            sensor_timestamp=data.get("timestamp"),
            received_at=received_at,
        )

        detect_threshold_alerts(
            device_id, temperature, humidity, received_at
        )

        check_anomaly(
            device_id, "temperature_c", temperature, history, received_at
        )
        check_anomaly(
            device_id, "humidity_pct", humidity, history, received_at
        )

        print(
            f"[SAVED] {device_id} | "
            f"{temperature:.2f} °C | {humidity:.2f}% RH "
            f"| record {telemetry_id}"
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"[INVALID PAYLOAD] {message.topic}: {exc}")

    except Exception as exc:
        print(f"[PROCESSING ERROR] {message.topic}: {exc}")


def main():
    initialize_database()
    print("[DATABASE READY]")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="mqtt-insight-processor",
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    print(f"Connecting to {BROKER_HOST}:{BROKER_PORT}...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping telemetry processor...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
