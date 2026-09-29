CREATE TABLE IF NOT EXISTS readings (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    device_id   TEXT NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    humidity    DOUBLE PRECISION,
    ambient     DOUBLE PRECISION,
    setpoint    DOUBLE PRECISION NOT NULL,
    mode        TEXT NOT NULL            -- HEAT / COOL / OFF
);
CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings (ts DESC);

CREATE TABLE IF NOT EXISTS control_events (
    id     BIGSERIAL PRIMARY KEY,
    ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
    action TEXT NOT NULL,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON control_events (ts DESC);
