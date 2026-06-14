from __future__ import annotations

import json
from datetime import datetime, timezone

from subscriber.sensor_store import SensorStore

REQUIRED_FIELDS = {
    "plant_code",
    "zone",
    "floor_level",
    "sensor_type",
    "value",
    "stage",
    "stage_code",
    "growth_day",
    "timestamp",
    "alarm",
}


def validate_payload(data: dict) -> None:
    missing = REQUIRED_FIELDS.difference(data)
    if missing:
        raise ValueError(f"Eksik sensör alanları: {sorted(missing)}")
    if not isinstance(data["value"], (int, float)):
        raise ValueError("Sensör değeri sayısal olmalıdır.")
    if not isinstance(data["alarm"], bool):
        raise ValueError("Alarm alanı boolean olmalıdır.")


def process_message(
    store: SensorStore,
    topic: str,
    payload: bytes | str,
    received_at: float | None = None,
) -> dict | None:
    if "/alarm/" in topic:
        return None

    raw_payload = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    data = json.loads(raw_payload)
    validate_payload(data)

    received_timestamp = received_at or datetime.now(timezone.utc).timestamp()
    latency_ms = round(
        (received_timestamp - float(data["timestamp"])) * 1000,
        2,
    )
    store.write(data)

    return {
        "data": data,
        "latency_ms": latency_ms,
        "alarm_written": data["alarm"],
    }
