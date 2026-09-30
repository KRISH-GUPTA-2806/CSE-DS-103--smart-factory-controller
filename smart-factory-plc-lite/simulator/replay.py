"""Replay public UCI datasets over encrypted MQTT while simulating a PLC."""

import argparse
import base64
import json
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from ucimlrepo import fetch_ucirepo

load_dotenv()


def cipher():
    key = bytes.fromhex(os.getenv("AES_GCM_KEY", ""))

    if len(key) != 32:
        raise SystemExit(
            "AES_GCM_KEY must be a 64-character hex string in .env"
        )

    return AESGCM(key)


def encrypt(value):
    nonce = os.urandom(12)
    ciphertext = cipher().encrypt(
        nonce,
        json.dumps(value).encode("utf-8"),
        b"factory-demo-v1",
    )

    envelope = {
        "v": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }

    return json.dumps(envelope)


def decrypt(payload):
    envelope = json.loads(payload)

    cleartext = cipher().decrypt(
        base64.b64decode(envelope["nonce"]),
        base64.b64decode(envelope["ciphertext"]),
        b"factory-demo-v1",
    )

    return json.loads(cleartext)


def load_energy():
    dataset = fetch_ucirepo(id=851)
    return dataset.data.original.copy()


def load_occupancy():
    dataset = fetch_ucirepo(id=864)
    return pd.concat(
        [dataset.data.features, dataset.data.targets],
        axis=1,
    )


def train_maintenance_model():
    dataset = fetch_ucirepo(id=601)
    frame = pd.concat(
        [dataset.data.features, dataset.data.targets],
        axis=1,
    )
    frame.columns = [str(column).strip() for column in frame.columns]

    def normalize(name):
        return "".join(
            character.lower()
            for character in name
            if character.isalnum()
        )

    def find_column(prefix):
        for column in frame.columns:
            if normalize(column).startswith(prefix):
                return column

        raise KeyError(
            f"Could not find a column starting with {prefix!r}. "
            f"Available columns: {list(frame.columns)}"
        )

    feature_names = [
        find_column("airtemperature"),
        find_column("processtemperature"),
        find_column("rotationalspeed"),
        find_column("torque"),
        find_column("toolwear"),
    ]
    target_name = find_column("machinefailure")

    features = frame[feature_names].astype(float)
    target = frame[target_name].astype(int)

    train_indices, holdout_indices = train_test_split(
        np.arange(len(frame)),
        test_size=0.2,
        random_state=42,
        stratify=target,
    )

    model = RandomForestClassifier(
        n_estimators=160,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        features.iloc[train_indices],
        target.iloc[train_indices],
    )

    holdout = (
        frame.iloc[holdout_indices]
        .sort_index()
        .reset_index(drop=True)
    )

    return model, holdout, feature_names


def get_value(row, names):
    lookup = {
        str(key).strip().lower(): key
        for key in row.index
    }

    for name in names:
        key = lookup.get(name.lower())

        if key is not None and pd.notna(row[key]):
            return float(row[key])

    return None


def occupancy_timestamp(row):
    lookup = {
        str(key).strip().lower(): key
        for key in row.index
    }

    date_key = lookup.get("date")
    time_key = lookup.get("time")
    date_value = row.get(date_key) if date_key else None
    time_value = row.get(time_key) if time_key else None

    if pd.notna(date_value) and pd.notna(time_value):
        return pd.to_datetime(
            f"{date_value} {time_value}",
            errors="coerce",
        )

    return pd.to_datetime(date_value, errors="coerce")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between published readings",
    )
    parser.add_argument(
        "--repeat",
        action="store_true",
        help="Replay the datasets continuously",
    )
    args = parser.parse_args()

    host = os.getenv("MQTT_HOST", "")
    username = os.getenv("MQTT_USERNAME", "")
    password = os.getenv("MQTT_PASSWORD", "")

    if not all((host, username, password)):
        raise SystemExit(
            "Set MQTT_HOST, MQTT_USERNAME, and MQTT_PASSWORD in .env"
        )

    telemetry_topic = os.getenv(
        "MQTT_TOPIC",
        "factory/demo/telemetry",
    )
    command_topic = os.getenv(
        "MQTT_COMMAND_TOPIC",
        "factory/demo/commands",
    )

    energy_rows = load_energy()
    occupancy_rows = load_occupancy()
    maintenance_model, maintenance_rows, maintenance_features = (
        train_maintenance_model()
    )

    energy_rows.columns = [
        str(column).strip()
        for column in energy_rows.columns
    ]
    occupancy_rows.columns = [
        str(column).strip()
        for column in occupancy_rows.columns
    ]

    energy_rows["date"] = pd.to_datetime(
        energy_rows["date"],
        dayfirst=True,
        errors="coerce",
    )
    energy_rows = (
        energy_rows
        .dropna(subset=["date", "Usage_kWh"])
        .reset_index(drop=True)
    )
    occupancy_rows = occupancy_rows.reset_index(drop=True)

    equipment = {
        "lights": "off",
        "fan": "off",
        "exhaust": "on",
        "machinery": "on",
    }
    manual_overrides = set()
    runtime_hours = {
        name: 0.0
        for name in equipment
    }
    previous_energy_timestamp = None

    high_demand_threshold = float(
        energy_rows["Usage_kWh"].quantile(0.9)
    )

    def on_command(client, userdata, message):
        try:
            command = decrypt(message.payload)
            name = command.get("equipment")
            action = command.get("action")

            if name not in equipment:
                return

            if action == "auto":
                manual_overrides.discard(name)
            elif action in {"on", "off"}:
                equipment[name] = action
                manual_overrides.add(name)

            print(f"Command received: {name} -> {action}")

        except Exception as exc:
            print(f"Ignoring invalid command: {exc}")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="factory-simulator",
    )
    client.username_pw_set(username, password)
    client.tls_set()
    client.on_message = on_command
    client.connect(
        host,
        int(os.getenv("MQTT_PORT", "8883")),
        keepalive=60,
    )
    client.subscribe(command_topic, qos=1)
    client.loop_start()

    try:
        while True:
            for energy_index, energy in energy_rows.iterrows():
                occupancy = occupancy_rows.iloc[
                    energy_index % len(occupancy_rows)
                ]
                maintenance = maintenance_rows.iloc[
                    energy_index % len(maintenance_rows)
                ]

                people_count = int(
                    get_value(
                        occupancy,
                        ["Room_Occupancy_Count"],
                    )
                    or 0
                )
                usage_kwh = float(energy["Usage_kWh"])

                maintenance_sensors = {
                    name: float(maintenance[name])
                    for name in maintenance_features
                }
                model_input = pd.DataFrame(
                    [maintenance_sensors],
                    columns=maintenance_features,
                )
                failure_class_index = list(
                    maintenance_model.classes_
                ).index(1)
                failure_risk = float(
                    maintenance_model.predict_proba(
                        model_input
                    )[0][failure_class_index]
                )

                # Simulated automatic control based on occupancy
                # and demand, unless that output has a manual override.
                if "lights" not in manual_overrides:
                    equipment["lights"] = (
                        "on" if people_count > 0 else "off"
                    )

                if "fan" not in manual_overrides:
                    equipment["fan"] = (
                        "on"
                        if (
                            people_count >= 2
                            and usage_kwh <= high_demand_threshold
                        )
                        else "off"
                    )

                temperatures = [
                    float(occupancy[column])
                    for column in occupancy.index
                    if (
                        "temp" in str(column).lower()
                        and pd.notna(occupancy[column])
                    )
                ]
                light_values = [
                    float(occupancy[column])
                    for column in occupancy.index
                    if (
                        "light" in str(column).lower()
                        and pd.notna(occupancy[column])
                    )
                ]
                co2_values = [
                    float(occupancy[column])
                    for column in occupancy.index
                    if (
                        "co2" in str(column).lower()
                        and pd.notna(occupancy[column])
                    )
                ]
                pir_values = [
                    int(float(occupancy[column]))
                    for column in occupancy.index
                    if (
                        "pir" in str(column).lower()
                        and pd.notna(occupancy[column])
                    )
                ]

                energy_timestamp = energy["date"]

                if previous_energy_timestamp is not None:
                    elapsed_hours = max(
                        0.0,
                        min(
                            (
                                energy_timestamp
                                - previous_energy_timestamp
                            ).total_seconds()
                            / 3600,
                            2.0,
                        ),
                    )

                    for name, state in equipment.items():
                        if state == "on":
                            runtime_hours[name] += elapsed_hours

                previous_energy_timestamp = energy_timestamp

                occupancy_time = occupancy_timestamp(occupancy)
                occupancy_time_utc = (
                    occupancy_time
                    .to_pydatetime()
                    .replace(tzinfo=timezone.utc)
                    .isoformat()
                )

                payload = {
                    # Receipt/replay timestamp used by the app.
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),

                    # Energy dataset reading.
                    "usage_kwh": usage_kwh,
                    "reactive_power_kvarh": get_value(
                        energy,
                        ["Lagging_Current_Reactive.Power_kVarh"],
                    ),
                    "power_factor": get_value(
                        energy,
                        ["Lagging_Current_Power_Factor"],
                    ),
                    "load_type": str(
                        energy.get("Load_Type", "Unknown")
                    ),
                    "energy_dataset_timestamp": (
                        energy_timestamp
                        .to_pydatetime()
                        .replace(tzinfo=timezone.utc)
                        .isoformat()
                    ),

                    # Occupancy dataset reading.
                    "people_count": people_count,
                    "room_temperature": (
                        sum(temperatures) / len(temperatures)
                        if temperatures else None
                    ),
                    "room_humidity": get_value(
                        occupancy,
                        ["Humidity", "S1_Humidity", "S2_Humidity"],
                    ),
                    "room_light": (
                        sum(light_values) / len(light_values)
                        if light_values else None
                    ),
                    "room_co2": (
                        sum(co2_values) / len(co2_values)
                        if co2_values else None
                    ),
                    "room_pir": (
                        sum(pir_values)
                        if pir_values else None
                    ),
                    "occupancy_dataset_timestamp": occupancy_time_utc,

                    # AI4I machine sample and model output.
                    "maintenance_risk": round(failure_risk, 5),
                    "machine_failure": int(
                        maintenance["Machine failure"]
                    ),
                    "maintenance_sensors": maintenance_sensors,
                    "maintenance_source_record": int(
                        maintenance.get("UDI", energy_index)
                    ),

                    # Software-simulated controller state.
                    "equipment": dict(equipment),
                    "equipment_runtime_hours": {
                        name: round(value, 3)
                        for name, value in runtime_hours.items()
                    },
                    "control_mode": (
                        "manual override"
                        if manual_overrides
                        else "automatic"
                    ),
                    "source": (
                        "uci-steel-energy+uci-room-occupancy"
                        "+uci-ai4i-maintenance"
                    ),
                }

                client.publish(
                    telemetry_topic,
                    encrypt(payload),
                    qos=1,
                )

                print(
                    f"Published {energy_timestamp} · "
                    f"{usage_kwh:.2f} kWh · "
                    f"room count {people_count}"
                )
                time.sleep(args.interval)

            if not args.repeat:
                break

    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()