import random
import time
import json
from datetime import datetime

import paho.mqtt.client as mqtt

from config import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, ENERGY_TOPIC


def generate_energy_data():
    voltage = round(random.uniform(220, 240), 2)
    current = round(random.uniform(2, 10), 2)

    power = round(voltage * current, 2)

    power_factor = round(random.uniform(0.80, 0.99), 2)

    energy = round(power / 1000, 3)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "voltage": voltage,
        "current": current,
        "power": power,
        "power_factor": power_factor,
        "energy": energy
    }


# Create MQTT client
client = mqtt.Client()

# Login to HiveMQ Cloud
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Enable TLS because HiveMQ Cloud uses port 8883
client.tls_set()

print("Connecting to HiveMQ Cloud...")

client.connect(MQTT_BROKER, MQTT_PORT, 60)

print("SUCCESS: Connected to HiveMQ Cloud!")
print("Publishing energy data...")
print("Topic:", ENERGY_TOPIC)


# Start MQTT network loop
client.loop_start()

try:
    while True:
        data = generate_energy_data()

        # Convert dictionary to JSON
        message = json.dumps(data)

        # Publish to HiveMQ
        client.publish(ENERGY_TOPIC, message)

        # Also show what was published
        print("Published:", data)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopping energy simulator...")

finally:
    client.loop_stop()
    client.disconnect()