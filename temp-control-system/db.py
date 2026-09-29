import time
import psycopg2
import config


def connect(retries=15, delay=3):
    for i in range(retries):
        try:
            conn = psycopg2.connect(
                host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
                user=config.DB_USER, password=config.DB_PASSWORD,
            )
            conn.autocommit = True
            return conn
        except psycopg2.OperationalError as e:
            print(f"[db] not ready ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise SystemExit("Could not connect to PostgreSQL. Is `docker compose up -d` running?")


def insert_reading(conn, device_id, temperature, humidity, ambient, setpoint, mode):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO readings (device_id, temperature, humidity, ambient, setpoint, mode) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (device_id, temperature, humidity, ambient, setpoint, mode),
        )


def insert_event(conn, action, reason):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO control_events (action, reason) VALUES (%s,%s)", (action, reason))
