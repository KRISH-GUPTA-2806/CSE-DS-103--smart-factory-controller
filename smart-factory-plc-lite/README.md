# Smart Factory PLC-Lite: software-only demo

An end-to-end simulation of the project brief. It uses public datasets for energy, occupancy, and predictive-maintenance signals, while simulating factory equipment and the controller so the system can run without hardware.

## Features

- Dashboard for energy, people count, environment readings, equipment state, and replay-based operating hours.
- Simulated equipment commands sent from React through FastAPI and HiveMQ Cloud to the Python simulator.
- Lights respond to occupancy; the fan responds to occupancy and energy demand.
- One-time on/off schedules.
- A Random Forest energy forecast for the next twelve 15-minute intervals.
- Load-saving recommendations based on occupancy, demand, and the forecast.
- Energy anomaly alerts using median/MAD scoring.
- A Random Forest machine-failure risk estimate from held-out AI4I examples.
- MQTT TLS and AES-GCM protection for message contents; HTTP Basic login for the local dashboard/API.
- Docker Compose services for PostgreSQL and the FastAPI backend.

This is a software demonstration, not a certified industrial controller. It cannot measure a real factory, prove actual energy savings, or operate physical machinery.

## Public datasets

The simulator downloads these from the UCI Machine Learning Repository on its first run:

1. [Steel Industry Energy Consumption, dataset 851](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption): historical energy readings from a steel industry.
2. [Room Occupancy Estimation, dataset 864](https://archive.ics.uci.edu/dataset/864/room+occupancy+estimation): measured room occupancy counts and environmental/PIR sensor readings.
3. [AI4I 2020 Predictive Maintenance, dataset 601](https://archive.ics.uci.edu/dataset/601/ai4i): machine sensor values and failure labels. UCI describes this as a synthetic dataset.

These datasets describe different sources and time periods. The simulator replays them together by row position to demonstrate the software; that does not mean the readings came from one factory or occurred at the same time. Equipment states and responses to commands are simulated. Retain dataset attribution and CC BY 4.0 licensing notices when redistributing dataset-derived work.

## Prerequisites

- Docker Desktop
- Python 3.11 or newer
- Node.js 20 or newer
- A HiveMQ Cloud cluster and MQTT username/password
- Internet access for the simulator's first run

## Configure

From the project root in PowerShell, copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set `MQTT_HOST`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `APP_PASSWORD`, and `POSTGRES_PASSWORD`.

Generate a shared MQTT payload key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated 64-character hex string into `AES_GCM_KEY`. Use the same `.env` for the API and simulator. Do not commit or share it.

## Start the project

### 1. Start PostgreSQL and the API

In PowerShell, change into the `infra` folder and run:

```powershell
docker compose --env-file ../.env up --build -d
```

The API health endpoint is `http://localhost:8000/health`. The API port is bound to this computer only.

### 2. Start the simulator

In a second PowerShell window, change into the `simulator` folder and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python replay.py --interval 2 --repeat
```

The first run downloads the three UCI datasets and trains the machine-failure model. It publishes one combined demo message every two seconds. Press `Ctrl+C` to stop it.

### 3. Start the React dashboard

In a third PowerShell window, change into the `frontend` folder and run:

```powershell
npm install
npm run dev
```

Open the local address printed by Vite, usually `http://localhost:5173`. Sign in with `APP_USERNAME` and `APP_PASSWORD` from `.env`. The dashboard refreshes every three seconds.

### Stop Docker services

From the `infra` folder, run:

```powershell
docker compose --env-file ../.env down
```

This preserves the PostgreSQL volume.

## Security notes

AES-GCM encrypts and authenticates MQTT message contents using a shared key. MQTT TLS also protects the connection to HiveMQ Cloud. This demo does not implement secure key rotation or production key management.

The dashboard uses HTTP Basic authentication and is intended for local use. Do not expose the API or dashboard to the public internet without HTTPS, stronger session management, and a reviewed deployment configuration.

## Project layout

```text
backend/       FastAPI API, database access, MQTT subscriber, and analytics
frontend/      React monitoring/control dashboard
simulator/     Dataset downloads, model, MQTT publisher, and PLC simulation
infra/         Docker Compose and PostgreSQL schema
```