import paho.mqtt.client as mqtt
import json
import time

# HiveMQ Cloud details
broker = "daac772232f54dd98bb0b5e46ae7ac47.s1.eu.hivemq.cloud"
port = 8883

username = "krish_gupta_2806"
password = "09923460930"

topic = "sensor/temp"

payload = {
    "device_id": "ESP32_001",
    "temperature": 25.4,
    "humidity": 60
}

# Create MQTT client
client = mqtt.Client()

# Authentication
client.username_pw_set(username, password)

# Enable TLS
client.tls_set()

# Connect to HiveMQ Cloud
client.connect(broker, port, 60)

# Measure publishing time
start = time.time()

result = client.publish(
    topic,
    json.dumps(payload)
)

result.wait_for_publish()

end = time.time()

print("Published")
print("Time :", round((end - start) * 1000, 2), "ms")

client.disconnect()