
from datetime import datetime, timezone

from database import get_recent_alerts
from processor import check_anomaly

TEST_DEVICE = "anomaly-test-device"

# Stable but non-identical historical values.
history = [
    {"temperature_c": value}
    for value in [
        24.8, 25.0, 25.1, 24.9, 25.2,
        24.7, 25.0, 25.1, 24.9, 25.0,
        25.2, 24.8, 25.1, 24.9, 25.0,
    ]
]

test_value = 45.0
timestamp = datetime.now(timezone.utc).isoformat()

print("Testing statistical anomaly detection...")
print(f"Device: {TEST_DEVICE}")
print(f"Historical readings: {len(history)}")
print(f"Test temperature: {test_value} °C")

check_anomaly(
    device_id=TEST_DEVICE,
    metric="temperature_c",
    current_value=test_value,
    history=history,
    timestamp=timestamp,
)

alerts = get_recent_alerts(100)
matching = [
    alert for alert in alerts
    if alert["device_id"] == TEST_DEVICE
    and alert["alert_type"] == "anomaly"
    and alert["created_at"] == timestamp
]

if matching:
    print("\nPASS: Anomaly detected and saved to SQLite.")
    print(matching[0]["message"])
else:
    print("\nFAIL: Expected anomaly alert was not found.")
