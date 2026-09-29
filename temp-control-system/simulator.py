"""Simulated room + heater/cooler. Publishes temperature, obeys commands."""
import json
import random
import time
from datetime import datetime, timezone

import config

state = {"mode": "OFF"}
temp = 27.0          # starting room temperature (deg C)
ambient = 30.0       # outside temperature
LOSS = 0.02          # heat exchange with ambient per second
HEAT_RATE = 0.35     # deg C/s gain when heating
COOL_RATE = 0.35     # deg C/s loss when cooling


def on_connect(client, userdata, flags, rc, props=None):
    print("[sim] connected:", rc)
    client.subscribe(config.TOPIC_COMMAND, qos=1)


def on_message(client, userdata, msg):
    try:
        state["mode"] = json.loads(msg.payload)["mode"]
        print(f"[sim] command -> {state['mode']}")
    except Exception as e:
        print("[sim] bad command:", e)


def main():
    global temp, ambient
    client = config.make_mqtt_client("tempctl-simulator")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()

    dt = config.PUBLISH_INTERVAL
    while True:
        ambient += random.uniform(-0.05, 0.05)
        delta = LOSS * (ambient - temp)
        if state["mode"] == "HEAT":
            delta += HEAT_RATE
        elif state["mode"] == "COOL":
            delta -= COOL_RATE
        temp += delta * dt / 2 + random.uniform(-0.05, 0.05)
        payload = {
            "device_id": config.DEVICE_ID,
            "temperature": round(temp, 2),
            "humidity": round(random.uniform(40, 60), 1),
            "ambient": round(ambient, 2),
            "mode": state["mode"],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        client.publish(config.TOPIC_SENSOR, json.dumps(payload), qos=1)
        print("[sim] published", payload["temperature"], state["mode"])
        time.sleep(dt)


if __name__ == "__main__":
    main()
