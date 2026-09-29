"""Subscribes to sensor data, runs hysteresis control, stores to PostgreSQL,
publishes HEAT/COOL/OFF commands back through HiveMQ."""
import json

import config
import db

conn = db.connect()
state = {"mode": "OFF", "setpoint": config.DEFAULT_SETPOINT}


def decide(temp, sp, mode):
    b = config.HYSTERESIS
    if temp < sp - b:
        return "HEAT"
    if temp > sp + b:
        return "COOL"
    if mode == "HEAT" and temp >= sp:
        return "OFF"
    if mode == "COOL" and temp <= sp:
        return "OFF"
    return mode


def on_connect(client, userdata, flags, rc, props=None):
    print("[ctl] connected:", rc)
    client.subscribe([(config.TOPIC_SENSOR, 1), (config.TOPIC_SETPOINT, 1)])


def on_message(client, userdata, msg):
    try:
        if msg.topic == config.TOPIC_SETPOINT:
            sp = max(10.0, min(35.0, float(msg.payload.decode().strip())))
            state["setpoint"] = sp
            db.insert_event(conn, "SETPOINT", f"setpoint changed to {sp}")
            print(f"[ctl] setpoint = {sp}")
            return

        data = json.loads(msg.payload)
        temp = float(data["temperature"])
        new_mode = decide(temp, state["setpoint"], state["mode"])
        if new_mode != state["mode"]:
            client.publish(config.TOPIC_COMMAND, json.dumps({"mode": new_mode}), qos=1, retain=True)
            db.insert_event(conn, new_mode, f"temp {temp} vs setpoint {state['setpoint']}")
            print(f"[ctl] {state['mode']} -> {new_mode}")
            state["mode"] = new_mode
        db.insert_reading(conn, data.get("device_id", config.DEVICE_ID), temp,
                          data.get("humidity"), data.get("ambient"),
                          state["setpoint"], state["mode"])
    except Exception as e:
        print("[ctl] error:", e)


def main():
    client = config.make_mqtt_client("tempctl-controller")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
