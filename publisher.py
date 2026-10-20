
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
TOPIC = "mqtt-insight/sensors/room-01"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[ERROR] Broker connection failed: {reason_code}")
    else:
        print(f"[CONNECTED] {BROKER_HOST}:{BROKER_PORT}")
        print(f"[PUBLISHING] {TOPIC}")


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="mqtt-insight-sensor-room-01",
    protocol=mqtt.MQTTv311,
)

client.on_connect = on_connect
client.reconnect_delay_set(min_delay=1, max_delay=10)
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_start()

try:
    while not client.is_connected():
        time.sleep(0.1)

    sequence = 0

    while True:
        sequence += 1

        payload = {
            "device_id": "room-01",
            "temperature_c": round(random.uniform(20.0, 35.0), 2),
            "humidity_pct": round(random.uniform(35.0, 75.0), 2),
            "sequence": sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = client.publish(
            TOPIC,
            json.dumps(payload),
            qos=0,
        )
        result.wait_for_publish()

        print(f"[PUBLISHED] {json.dumps(payload)}")
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopping sensor simulator...")
finally:
    client.disconnect()
    client.loop_stop()
