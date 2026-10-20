
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TOPIC = "mqtt-insight/sensors/room-01"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[ERROR] Broker connection failed: {reason_code}")
        return

    print(f"[CONNECTED] {BROKER_HOST}:{BROKER_PORT}")
    client.subscribe(TOPIC, qos=0)
    print(f"[SUBSCRIBED] {TOPIC}")


def on_message(client, userdata, message):
    received_at = datetime.now(timezone.utc).isoformat()

    try:
        payload_text = message.payload.decode("utf-8")
        data = json.loads(payload_text)

        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")

        required = ("device_id", "temperature_c", "humidity_pct")

        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")

        temperature = float(data["temperature_c"])
        humidity = float(data["humidity_pct"])

        print("\n[TELEMETRY RECEIVED]")
        print(f"  Topic:       {message.topic}")
        print(f"  Device:      {data['device_id']}")
        print(f"  Temperature: {temperature:.1f} °C")
        print(f"  Humidity:    {humidity:.1f} %")
        print(f"  Received:    {received_at}")

    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"\n[INVALID PAYLOAD] Topic: {message.topic}")
        print(f"  Reason: {exc}")
        print(f"  Raw bytes: {message.payload!r}")


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="mqtt-insight-subscriber",
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
    print("\nStopping subscriber...")
finally:
    client.disconnect()
