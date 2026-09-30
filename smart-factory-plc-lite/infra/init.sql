CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL PRIMARY KEY,
    source_timestamp TIMESTAMPTZ NOT NULL,
    energy_dataset_timestamp TIMESTAMPTZ,
    occupancy_dataset_timestamp TIMESTAMPTZ,
    maintenance_source_record BIGINT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usage_kwh DOUBLE PRECISION NOT NULL,
    reactive_power_kvarh DOUBLE PRECISION,
    power_factor DOUBLE PRECISION,
    load_type TEXT,
    equipment JSONB NOT NULL DEFAULT '{}'::jsonb,
    equipment_runtime_hours JSONB NOT NULL DEFAULT '{}'::jsonb,
    control_mode TEXT NOT NULL DEFAULT 'automatic',
    people_count INTEGER NOT NULL DEFAULT 0,
    room_temperature DOUBLE PRECISION,
    room_humidity DOUBLE PRECISION,
    room_light DOUBLE PRECISION,
    room_co2 DOUBLE PRECISION,
    room_pir INTEGER,
    maintenance_risk DOUBLE PRECISION,
    machine_failure INTEGER,
    maintenance_sensors JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'uci-steel-industry'
);

-- Add fields if this database was created from the earlier scaffold.
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS energy_dataset_timestamp TIMESTAMPTZ;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS occupancy_dataset_timestamp TIMESTAMPTZ;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS maintenance_source_record BIGINT;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS equipment_runtime_hours JSONB
        NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS control_mode TEXT
        NOT NULL DEFAULT 'automatic';
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS room_temperature DOUBLE PRECISION;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS room_humidity DOUBLE PRECISION;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS room_light DOUBLE PRECISION;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS room_co2 DOUBLE PRECISION;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS room_pir INTEGER;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS maintenance_risk DOUBLE PRECISION;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS machine_failure INTEGER;
ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS maintenance_sensors JSONB
        NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS telemetry_source_timestamp_idx
    ON telemetry (source_timestamp DESC);

CREATE TABLE IF NOT EXISTS schedules (
    id BIGSERIAL PRIMARY KEY,
    equipment TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('on', 'off')),
    run_at TIMESTAMPTZ NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    executed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS command_log (
    id BIGSERIAL PRIMARY KEY,
    equipment TEXT NOT NULL,
    action TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS alert_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE
);