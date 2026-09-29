# Temperature Control System
HiveMQ Cloud (MQTT) + Python + PostgreSQL + Grafana (Docker)

```
simulator.py --(tempctl/sensor/temperature)--> HiveMQ --> controller.py --> PostgreSQL --> Grafana
simulator.py <--(tempctl/actuator/command)---- HiveMQ <-- controller.py
you (HiveMQ web client) --(tempctl/setpoint: 22)--> controller.py
```

## Steps
1. HiveMQ Cloud: create cluster > Access Management > add credentials (Publish+Subscribe). Note host + port 8883.
2. `cp .env.example .env` and fill MQTT_HOST / MQTT_USERNAME / MQTT_PASSWORD.
3. `docker compose up -d`  (starts PostgreSQL + Grafana)
4. `python -m venv venv && venv\Scripts\activate` (Windows) then `pip install -r requirements.txt`
5. Terminal 1: `python controller.py`   Terminal 2: `python simulator.py`
6. Grafana: http://localhost:3000 (admin/admin) > Dashboards > Temperature Control System
7. Change setpoint: HiveMQ Cloud > Web Client > publish `22` to `tempctl/setpoint`.

Run everything in Docker instead: `docker compose --profile apps up -d --build`

Verify DB: `docker exec -it tempctl-postgres psql -U tempctl -d tempctl -c "select * from readings order by ts desc limit 5;"`
Reset: `docker compose down -v`
