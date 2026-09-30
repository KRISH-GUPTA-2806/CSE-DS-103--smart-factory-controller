from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.ensemble import RandomForestRegressor

from .db import (
    add_alert,
    add_schedule,
    delete_schedule,
    get_alerts,
    get_schedules,
    latest_rows,
    recent_commands,
)
from .mqtt_client import publish_command, start_subscriber, stop_subscriber
from .security import require_user


EQUIPMENT = {"lights", "fan", "exhaust", "machinery"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_subscriber()
    yield
    stop_subscriber()


app = FastAPI(
    title="Smart Factory PLC-Lite API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


class Command(BaseModel):
    equipment: str
    action: str


class Schedule(BaseModel):
    equipment: str
    action: str
    run_at: datetime


def validate_control(equipment, action):
    if equipment not in EQUIPMENT:
        raise HTTPException(422, "Unknown equipment")

    if action not in {"on", "off", "auto"}:
        raise HTTPException(
            422,
            "Action must be on, off, or auto",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/telemetry")
def telemetry(
    limit: int = Query(default=100, ge=1, le=1000),
    user=Depends(require_user),
):
    return latest_rows(limit)


@app.get("/api/analytics")
def analytics(user=Depends(require_user)):
    rows = list(reversed(latest_rows(1000)))

    if not rows:
        return {
            "forecast": [],
            "anomalies": [],
            "model": "waiting for data",
        }

    values = np.array(
        [float(row["usage_kwh"]) for row in rows]
    )

    # Flag unusually high or low energy readings using robust
    # median/MAD scoring.
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) or 0.0001
    anomaly_items = []

    for row, value in zip(rows, values):
        score = 0.6745 * abs(float(value) - median) / mad

        if score >= 3.5:
            anomaly_items.append(
                {
                    "timestamp": row["source_timestamp"],
                    "usage_kwh": float(value),
                    "score": round(score, 2),
                }
            )

    timestamps = [
        row["energy_dataset_timestamp"] or row["source_timestamp"]
        for row in rows
    ]

    features = np.array(
        [
            [stamp.hour, stamp.weekday(), stamp.month, stamp.day]
            for stamp in timestamps
        ]
    )

    forecast = []

    if len(rows) >= 20:
        model = RandomForestRegressor(
            n_estimators=80,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1,
        )
        model.fit(features, values)

        last_timestamp = timestamps[-1]
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(
                tzinfo=timezone.utc
            )

        future_times = [
            last_timestamp + timedelta(minutes=15 * index)
            for index in range(1, 13)
        ]

        future_features = np.array(
            [
                [stamp.hour, stamp.weekday(), stamp.month, stamp.day]
                for stamp in future_times
            ]
        )

        predictions = model.predict(future_features)
        forecast = [
            {
                "timestamp": stamp,
                "usage_kwh": round(float(value), 3),
            }
            for stamp, value in zip(future_times, predictions)
        ]

        model_name = (
            "Random Forest trained on replayed steel energy readings"
        )
    else:
        model_name = "Need at least 20 readings to train forecast"

    return {
        "forecast": forecast,
        "anomalies": anomaly_items[-10:],
        "model": model_name,
        "baseline_kwh": round(median, 3),
        "threshold_kwh": round(
            float(np.quantile(values, 0.9)),
            3,
        ),
    }


@app.post("/api/commands")
def command(body: Command, user=Depends(require_user)):
    validate_control(body.equipment, body.action)

    try:
        publish_command(body.equipment, body.action)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    return {
        "status": "sent",
        "equipment": body.equipment,
        "action": body.action,
    }


@app.post("/api/optimize")
def optimize(
    apply: bool = False,
    user=Depends(require_user),
):
    rows = latest_rows(100)

    if not rows:
        raise HTTPException(
            409,
            "Waiting for dataset replay before optimization",
        )

    latest = rows[0]
    energy = float(latest["usage_kwh"])
    occupancy = int(latest["people_count"] or 0)

    historical_values = np.array(
        [float(row["usage_kwh"]) for row in rows]
    )
    threshold = float(np.quantile(historical_values, 0.9))
    predicted = analytics(user)

    predicted_peak = max(
        (
            float(point["usage_kwh"])
            for point in predicted["forecast"]
        ),
        default=0.0,
    )

    equipment = latest["equipment"] or {}
    recommendations = []

    if occupancy == 0 and equipment.get("lights") == "on":
        recommendations.append(
            {
                "equipment": "lights",
                "action": "off",
                "reason": (
                    "Occupancy dataset indicates an empty room"
                ),
            }
        )

    if (
        occupancy <= 1
        and equipment.get("fan") == "on"
        and (energy > threshold or predicted_peak > threshold)
    ):
        recommendations.append(
            {
                "equipment": "fan",
                "action": "off",
                "reason": (
                    "Current or forecast demand is above the "
                    "historical 90th percentile while occupancy is low"
                ),
            }
        )

    # The demo policy never automatically switches off exhaust
    # or machinery.
    if apply:
        for item in recommendations:
            try:
                publish_command(
                    item["equipment"],
                    item["action"],
                    "optimizer",
                )
                add_alert(
                    "Optimizer requested "
                    f"{item['equipment']} {item['action']}: "
                    f"{item['reason']}",
                    "info",
                )
            except RuntimeError as exc:
                raise HTTPException(503, str(exc)) from exc

    return {
        "applied": apply,
        "current_usage_kwh": energy,
        "predicted_peak_kwh": round(predicted_peak, 3),
        "threshold_kwh": round(threshold, 3),
        "occupancy": occupancy,
        "recommendations": recommendations,
    }


@app.get("/api/schedules")
def schedules(user=Depends(require_user)):
    return get_schedules()


@app.post("/api/schedules")
def create_schedule(
    body: Schedule,
    user=Depends(require_user),
):
    validate_control(body.equipment, body.action)

    if body.action == "auto":
        raise HTTPException(
            422,
            "Scheduled action must be on or off",
        )

    if body.run_at.tzinfo is None:
        raise HTTPException(
            422,
            "run_at must include a timezone",
        )

    if body.run_at <= datetime.now(timezone.utc):
        raise HTTPException(
            422,
            "run_at must be in the future",
        )

    return add_schedule(
        body.equipment,
        body.action,
        body.run_at,
    )


@app.delete("/api/schedules/{schedule_id}")
def remove_schedule(
    schedule_id: int,
    user=Depends(require_user),
):
    if not delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")

    return {"deleted": schedule_id}


@app.get("/api/alerts")
def alerts(user=Depends(require_user)):
    analytics_data = analytics(user)

    return {
        "stored": get_alerts(20),
        "detected_anomalies": analytics_data["anomalies"],
    }


@app.get("/api/commands")
def commands(user=Depends(require_user)):
    return recent_commands()