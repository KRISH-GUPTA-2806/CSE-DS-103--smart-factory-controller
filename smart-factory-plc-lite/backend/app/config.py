import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://factory:change-me@localhost:5432/factory",
)

MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "factory/demo/telemetry")
MQTT_COMMAND_TOPIC = os.getenv(
    "MQTT_COMMAND_TOPIC",
    "factory/demo/commands",
)

AES_GCM_KEY = os.getenv("AES_GCM_KEY", "")
APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "change-this-password")