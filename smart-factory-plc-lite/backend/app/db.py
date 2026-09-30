import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .config import DATABASE_URL


def connect():
    url = DATABASE_URL.replace(
        "postgresql+psycopg://",
        "postgresql://",
    )
    return psycopg.connect(url, row_factory=dict_row)


def latest_rows(limit=100):
    with connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM telemetry
            ORDER BY received_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()


def insert_telemetry(message):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO telemetry (
                source_timestamp,
                energy_dataset_timestamp,
                occupancy_dataset_timestamp,
                maintenance_source_record,
                usage_kwh,
                reactive_power_kvarh,
                power_factor,
                load_type,
                equipment,
                equipment_runtime_hours,
                control_mode,
                people_count,
                room_temperature,
                room_humidity,
                room_light,
                room_co2,
                room_pir,
                maintenance_risk,
                machine_failure,
                maintenance_sensors,
                source
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                message["timestamp"],
                message.get("energy_dataset_timestamp"),
                message.get("occupancy_dataset_timestamp"),
                message.get("maintenance_source_record"),
                message["usage_kwh"],
                message.get("reactive_power_kvarh"),
                message.get("power_factor"),
                message.get("load_type"),
                Jsonb(message.get("equipment", {})),
                Jsonb(message.get("equipment_runtime_hours", {})),
                message.get("control_mode", "automatic"),
                message.get("people_count", 0),
                message.get("room_temperature"),
                message.get("room_humidity"),
                message.get("room_light"),
                message.get("room_co2"),
                message.get("room_pir"),
                message.get("maintenance_risk"),
                message.get("machine_failure"),
                Jsonb(message.get("maintenance_sensors", {})),
                message.get("source", "uci-steel-industry"),
            ),
        )


def get_schedules():
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM schedules ORDER BY run_at"
        ).fetchall()


def add_schedule(equipment, action, run_at):
    with connect() as conn:
        return conn.execute(
            """
            INSERT INTO schedules (equipment, action, run_at)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (equipment, action, run_at),
        ).fetchone()


def delete_schedule(schedule_id):
    with connect() as conn:
        return conn.execute(
            "DELETE FROM schedules WHERE id = %s RETURNING id",
            (schedule_id,),
        ).fetchone()


def due_schedules():
    with connect() as conn:
        return conn.execute(
            """
            UPDATE schedules
            SET enabled = FALSE, executed_at = NOW()
            WHERE enabled = TRUE AND run_at <= NOW()
            RETURNING *
            """
        ).fetchall()


def log_command(equipment, action, source):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO command_log (equipment, action, source)
            VALUES (%s, %s, %s)
            """,
            (equipment, action, source),
        )


def recent_commands(limit=20):
    with connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM command_log
            ORDER BY requested_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()


def add_alert(message, severity="warning"):
    with connect() as conn:
        return conn.execute(
            """
            INSERT INTO alert_log (severity, message)
            VALUES (%s, %s)
            RETURNING *
            """,
            (severity, message),
        ).fetchone()


def get_alerts(limit=20):
    with connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM alert_log
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()