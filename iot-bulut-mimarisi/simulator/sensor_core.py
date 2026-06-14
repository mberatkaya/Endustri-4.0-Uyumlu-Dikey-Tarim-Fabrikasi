from __future__ import annotations

import json
import random
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from config import ALARM_THRESHOLDS, GROWTH_STAGES, UNITS

EC_TO_TDS = 640.0


def get_stage_by_day(day: int) -> dict:
    if day <= GROWTH_STAGES[0]["day_start"]:
        return GROWTH_STAGES[0]
    for stage in GROWTH_STAGES:
        if stage["day_start"] <= day <= stage["day_end"]:
            return stage
    return GROWTH_STAGES[-1]


def generate_value(sensor: str, stage: dict) -> float:
    lower, upper, standard_deviation = stage["sensors"][sensor]
    value = random.gauss((lower + upper) / 2, standard_deviation)
    bounds = {
        "ph": (4.0, 8.5),
        "ec": (0.0, 4.0),
        "temperature": (10.0, 35.0),
        "humidity": (30.0, 100.0),
        "co2": (200.0, 2000.0),
        "light": (0.0, 500.0),
    }
    physical_lower, physical_upper = bounds.get(sensor, (-9999, 9999))
    return round(max(physical_lower, min(physical_upper, value)), 2)


def is_alarm(sensor: str, value: float) -> bool:
    lower, upper = ALARM_THRESHOLDS.get(sensor, (None, None))
    return lower is not None and (value < lower or value > upper)


class Plant:
    def __init__(self, zone: str, floor: int, growth_day: int):
        self.zone = zone
        self.floor = floor
        self.growth_day = growth_day
        self.code = f"Z{zone[-1]}-F{floor}"

    def stage(self) -> dict:
        return get_stage_by_day(self.growth_day)

    def measure(self) -> list[dict]:
        stage = self.stage()
        timestamp = datetime.now(timezone.utc).timestamp()
        rows = []
        for sensor in stage["sensors"]:
            value = generate_value(sensor, stage)
            rows.append(
                {
                    "plant_code": self.code,
                    "zone": self.zone,
                    "floor_level": self.floor,
                    "sensor_type": sensor,
                    "value": value,
                    "tds_value": round(value * EC_TO_TDS, 1) if sensor == "ec" else None,
                    "unit": UNITS.get(sensor, ""),
                    "stage": stage["name"],
                    "stage_code": stage["code"],
                    "growth_day": self.growth_day,
                    "timestamp": timestamp,
                    "alarm": is_alarm(sensor, value),
                }
            )
        return rows


def publish(client: mqtt.Client, row: dict) -> None:
    topic = f"dikeytarim/{row['zone']}/floor" f"{row['floor_level']}/{row['sensor_type']}"
    payload = json.dumps(row, default=str)
    client.publish(topic, payload, qos=1)
    if row["alarm"]:
        client.publish(
            f"dikeytarim/alarm/{row['plant_code']}",
            payload,
            qos=2,
        )
