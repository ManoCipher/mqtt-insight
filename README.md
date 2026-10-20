# MQTT Insight

**IoT Telemetry Monitoring and Anomaly Detection**

MQTT Insight is a small Python demonstration project that simulates sensor telemetry, receives messages over MQTT, stores readings and alerts in SQLite, and presents recent data in a Streamlit dashboard.

## Features

- **MQTT telemetry publisher** — simulates a sensor named `room-01` and publishes JSON readings approximately every two seconds.
- **MQTT subscriber** — optional diagnostic client that prints incoming telemetry without writing it to the database.
- **Telemetry processor** — subscribes to `mqtt-insight/sensors/#`, validates messages, stores readings, and evaluates alert conditions.
- **Threshold alerts** — temperature warnings outside 10–32 °C and humidity warnings outside 20–80%. Temperature readings above 35 °C are marked critical.
- **Statistical anomaly detection** — uses the median absolute deviation (MAD) and modified z-score for temperature and humidity, after enough historical samples are available.
- **SQLite persistence** — stores telemetry and alert history in `data/mqtt_insight.db`.
- **Streamlit dashboard** — displays latest measurements, telemetry trends, device online/stale status, recent alerts, and readings.
- **Anomaly test script** — checks that an extreme test value produces an anomaly alert saved in SQLite.

## Architecture

```text
publisher.py  ──MQTT──>  Mosquitto broker  ──MQTT──>  processor.py
                                  │                         │
                                  └──> subscriber.py        ├──> database.py ──> SQLite
                                                            │
                                                            └──> threshold and anomaly alerts
                                                                      │
                                                                      v
                                                               dashboard.py
                                                               (Streamlit)
```

`subscriber.py` is optional and independent of the processing pipeline. It is useful for checking whether messages are being published and received.

## Requirements

- Python 3.10 or later is recommended.
- A running MQTT broker (the current scripts default to Mosquitto at `127.0.0.1:1883`).
- Windows PowerShell commands below assume the project is located at `D:\Zeta Innovate\mqtt-insight`. Adjust the path if needed.

Python dependencies are listed in `requirements.txt`:

- `paho-mqtt`
- `streamlit`
- `pandas`
- `streamlit-autorefresh`

## Setup on Windows

Open PowerShell in the project directory:

```powershell
cd "D:\Zeta Innovate\mqtt-insight"
```

Create and activate a virtual environment if one does not already exist:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell execution policy prevents activation, use the virtual-environment Python executable directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install and start Mosquitto separately if it is not already installed and running. The project scripts do not start the broker automatically. Do not start a second broker on the same port if a broker is already listening on port 1883.

## Run the application

Use separate PowerShell terminals for each long-running process. Start the broker first.

**Terminal 1 — telemetry processor**

```powershell
cd "D:\Zeta Innovate\mqtt-insight"
.\.venv\Scripts\python.exe processor.py
```

The processor initializes the database and subscribes to `mqtt-insight/sensors/#`.

**Terminal 2 — sensor publisher**

```powershell
cd "D:\Zeta Innovate\mqtt-insight"
.\.venv\Scripts\python.exe publisher.py
```

The publisher sends a JSON message about every two seconds to `mqtt-insight/sensors/room-01`. Press `Ctrl+C` to stop it.

**Terminal 3 — dashboard**

```powershell
cd "D:\Zeta Innovate\mqtt-insight"
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). The dashboard can be run before telemetry starts; it will display a prompt when no telemetry records exist.

**Optional — raw MQTT subscriber**

Run this in another terminal to inspect received messages:

```powershell
cd "D:\Zeta Innovate\mqtt-insight"
.\.venv\Scripts\python.exe subscriber.py
```

This subscriber prints messages and does not save them to SQLite.

## Database

The database path is `data/mqtt_insight.db`, relative to the project directory.

- `telemetry` stores device ID, topic, temperature, humidity, sensor timestamp, and receive timestamp.
- `alerts` stores device ID, alert type, severity, metric, value, message, and creation timestamp.

The processor creates the database and required tables when it starts. Keep a backup of the database before deleting or replacing it; it contains accumulated telemetry and alert history.

## Tests and final verification

Run the anomaly test from the project directory:

```powershell
.\.venv\Scripts\python.exe test_anomaly.py
```

The test uses a synthetic historical temperature series and a test value of 45 °C. A passing result should print `PASS: Anomaly detected and saved to SQLite.` The test writes a test alert to the project's database, so a record for `anomaly-test-device` may appear in the dashboard's alert history.

Manual integration checks:

1. **MQTT ingestion:** start the broker and processor, then start the publisher. Confirm that the processor prints `[SAVED]` messages and that telemetry appears in the dashboard.
2. **Threshold alert:** publish or otherwise simulate a reading beyond a configured threshold and confirm an alert is saved and visible in the dashboard.
3. **Offline-device status:** stop the publisher. After the dashboard's configured stale timeout elapses, confirm the device is marked `STALE`.
4. **Anomaly alert:** after at least ten historical readings with non-zero median absolute deviation are available for the device, send an unusual reading and confirm an anomaly alert is saved and displayed.
5. **Dashboard refresh:** use the refresh interval setting or `Refresh now` if the latest data is not immediately visible.

Previously reported regression results for threshold alerts, offline-device detection, and dashboard anomaly visibility were PASS. Re-run these checks in the target environment before presenting the project.

## Configuration and behavior

Current defaults are defined near the top of `publisher.py`, `processor.py`, and `dashboard.py`:

- MQTT broker: `127.0.0.1:1883`
- Publisher topic: `mqtt-insight/sensors/room-01`
- Processor subscription: `mqtt-insight/sensors/#`
- Temperature threshold range: 10–32 °C
- Humidity threshold range: 20–80%
- Minimum anomaly history: 10 samples
- Anomaly modified z-score threshold: 3.5
- Dashboard stale-timeout choices: 10, 15, 30, or 60 seconds

The publisher uses random values for demonstration; it is not connected to a physical sensor.

## Known limitations

- The sample publisher generates simulated telemetry rather than real sensor data.
- Threshold violations can create a new alert for each violating message. Alert deduplication, acknowledgement, and automatic resolution are not implemented.
- Anomaly detection skips a metric when the historical median absolute deviation is zero.
- The dashboard displays a recent alert history, not an alert workflow or incident-management system.
- The broker address and thresholds are constants in the source files rather than environment-based configuration.
- This is a local demonstration project; authentication, TLS, production deployment, multi-user access control, and operational monitoring are outside its current scope.

## Project files

```text
mqtt-insight/
├── dashboard.py       # Streamlit telemetry and alert dashboard
├── database.py        # SQLite schema and database operations
├── processor.py       # MQTT processing and alert detection
├── publisher.py       # Simulated sensor publisher
├── subscriber.py      # Optional MQTT message viewer
├── test_anomaly.py    # Statistical anomaly persistence test
├── requirements.txt   # Python dependencies
├── data/
│   └── mqtt_insight.db # Local telemetry and alert database
└── README.md
```

## Suggested demonstration sequence

1. Show the architecture and README.
2. Start Mosquitto and `processor.py`.
3. Start `publisher.py` and show incoming messages and stored telemetry.
4. Open the Streamlit dashboard and show temperature, humidity, trends, device health, and alert history.
5. Demonstrate a threshold alert, stop the publisher to show stale status, and run `test_anomaly.py` to demonstrate anomaly persistence.
6. Explain the documented limitations and possible future improvements.
