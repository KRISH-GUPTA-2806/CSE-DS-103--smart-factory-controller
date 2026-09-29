import os
from dotenv import load_dotenv

load_dotenv()

# MQTT (HiveMQ Cloud)
MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

TOPIC_SENSOR = "tempctl/sensor/temperature"     # simulator -> controller
TOPIC_COMMAND = "tempctl/actuator/command"      # controller -> simulator
TOPIC_SETPOINT = "tempctl/setpoint"             # you -> controller (plain number)

# Postgres
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "tempctl")
DB_USER = os.getenv("POSTGRES_USER", "tempctl")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "tempctl_pass")

# Control
DEFAULT_SETPOINT = float(os.getenv("DEFAULT_SETPOINT", "24.0"))
HYSTERESIS = float(os.getenv("HYSTERESIS", "0.5"))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "2"))
DEVICE_ID = "room-1"


def make_mqtt_client(client_id):
    """Build a TLS-enabled paho client for HiveMQ Cloud."""
    import paho.mqtt.client as mqtt
    if not MQTT_HOST:
        raise SystemExit("MQTT_HOST missing - copy .env.example to .env and fill it in.")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set()  # uses system CA certs; HiveMQ Cloud requires TLS
    return client
