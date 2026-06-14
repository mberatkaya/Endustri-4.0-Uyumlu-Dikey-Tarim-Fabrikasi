from __future__ import annotations

import json
from datetime import datetime, timezone

from config import ALARM_THRESHOLDS

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


def write_measurement(conn, data: dict) -> None:
    sql = """INSERT INTO measurements
        (plant_code, zone_name, floor_level, sensor_type, value, tds_value,
         unit, stage, stage_code, growth_day, alarm, measured_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))"""
    with conn.cursor() as cursor:
        cursor.execute(
            sql,
            (
                data.get("plant_code"),
                data.get("zone"),
                data.get("floor_level"),
                data.get("sensor_type"),
                data.get("value"),
                data.get("tds_value"),
                data.get("unit"),
                data.get("stage"),
                data.get("stage_code"),
                data.get("growth_day"),
                data.get("alarm"),
                data.get("timestamp"),
            ),
        )
    conn.commit()


def write_alarm(conn, data: dict) -> None:
    lower, upper = ALARM_THRESHOLDS.get(data.get("sensor_type", ""), (None, None))
    alarm_type = "low" if lower is not None and data["value"] < lower else "high"
    sql = """INSERT INTO alarms
        (plant_code, zone_name, floor_level, sensor_type, value, threshold_lo,
         threshold_hi, alarm_type, stage, growth_day, triggered_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))"""
    with conn.cursor() as cursor:
        cursor.execute(
            sql,
            (
                data.get("plant_code"),
                data.get("zone"),
                data.get("floor_level"),
                data.get("sensor_type"),
                data.get("value"),
                lower,
                upper,
                alarm_type,
                data.get("stage"),
                data.get("growth_day"),
                data.get("timestamp"),
            ),
        )
    conn.commit()


def process_message(
    conn,
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
    write_measurement(conn, data)
    if data["alarm"]:
        write_alarm(conn, data)

    return {
        "data": data,
        "latency_ms": latency_ms,
        "alarm_written": data["alarm"],
    }
