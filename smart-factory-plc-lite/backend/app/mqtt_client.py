import logging
import threading
import time

import paho.mqtt.client as mqtt

from .config import (
    MQTT_COMMAND_TOPIC,
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_TOPIC,
    MQTT_USERNAME,
)
from .db import add_alert, due_schedules, insert_telemetry, log_command
from .security import decrypt_message, encrypt_message

log = logging.getLogger(__name__)

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="factory-api",
)
connected = threading.Event()
stop_scheduler = threading.Event()


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(MQTT_TOPIC, qos=1)
        connected.set()
        log.info("Connected to HiveMQ Cloud")
    else:
        log.error("MQTT connection failed: %s", reason_code)


def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties,
):
    connected.clear()


def on_message(client, userdata, msg):
    try:
        message = decrypt_message(msg.payload)
        insert_telemetry(message)
    except Exception:
        log.exception(
            "Ignoring invalid or undecryptable telemetry message"
        )


def start_subscriber():
    if not all((MQTT_HOST, MQTT_USERNAME, MQTT_PASSWORD)):
        log.warning(
            "HiveMQ settings missing; MQTT features are unavailable"
        )
        return

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()

        threading.Thread(
            target=_schedule_loop,
            daemon=True,
        ).start()
    except OSError:
        log.exception("Could not reach HiveMQ Cloud")


def publish_command(equipment, action, source="manual"):
    if not connected.is_set():
        raise RuntimeError("HiveMQ Cloud is not connected")

    payload = encrypt_message(
        {
            "type": "command",
            "equipment": equipment,
            "action": action,
            "source": source,
        }
    )

    result = client.publish(
        MQTT_COMMAND_TOPIC,
        payload,
        qos=1,
    )

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError("MQTT publish failed")

    log_command(equipment, action, source)


def _schedule_loop():
    while not stop_scheduler.wait(2):
        if not connected.is_set():
            continue

        try:
            for item in due_schedules():
                try:
                    publish_command(
                        item["equipment"],
                        item["action"],
                        "schedule",
                    )
                except RuntimeError as exc:
                    add_alert(
                        f"Scheduled command could not be sent: {exc}",
                        "error",
                    )
        except Exception:
            log.exception("Schedule check failed")
            time.sleep(3)


def stop_subscriber():
    stop_scheduler.set()

    if client.is_connected():
        client.disconnect()

    client.loop_stop()
    connected.clear()