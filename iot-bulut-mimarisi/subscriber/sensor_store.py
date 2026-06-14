from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from config import ALARM_THRESHOLDS


class SensorStore(Protocol):
    def write(self, data: dict) -> None:
        """Persist one validated MQTT sensor payload."""


def _alarm_type(data: dict) -> str:
    lower, _ = ALARM_THRESHOLDS.get(data.get("sensor_type", ""), (None, None))
    if lower is not None and data["value"] < lower:
        return "low"
    return "high"


@dataclass
class PostgresSensorStore:
    connection: object

    def write(self, data: dict) -> None:
        measurement_sql = """INSERT INTO measurements
            (plant_code, zone_name, floor_level, sensor_type, value, tds_value,
             unit, stage, stage_code, growth_day, alarm, measured_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))"""
        alarm_sql = """INSERT INTO alarms
            (plant_code, zone_name, floor_level, sensor_type, value, threshold_lo,
             threshold_hi, alarm_type, stage, growth_day, triggered_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))"""

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute(
                    measurement_sql,
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
                if data["alarm"]:
                    lower, upper = ALARM_THRESHOLDS.get(data.get("sensor_type", ""), (None, None))
                    cursor.execute(
                        alarm_sql,
                        (
                            data.get("plant_code"),
                            data.get("zone"),
                            data.get("floor_level"),
                            data.get("sensor_type"),
                            data.get("value"),
                            lower,
                            upper,
                            _alarm_type(data),
                            data.get("stage"),
                            data.get("growth_day"),
                            data.get("timestamp"),
                        ),
                    )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


@dataclass
class SqlServerSensorStore:
    connection: object

    def write(self, data: dict) -> None:
        procedure_sql = """EXEC dbo.sp_SensorVerisiEkle
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?"""
        measured_at = datetime.fromtimestamp(float(data["timestamp"]), tz=timezone.utc).replace(
            tzinfo=None
        )

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute(
                    procedure_sql,
                    (
                        data.get("plant_code"),
                        measured_at,
                        data.get("sensor_type"),
                        data.get("value"),
                        data.get("tds_value"),
                        data.get("unit"),
                        data.get("stage"),
                        data.get("stage_code"),
                        data.get("growth_day"),
                        data.get("alarm"),
                    ),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def build_sensor_store(connection, engine: str) -> SensorStore:
    selected_engine = engine.lower()
    if selected_engine == "postgres":
        return PostgresSensorStore(connection)
    if selected_engine == "sqlserver":
        return SqlServerSensorStore(connection)
    raise ValueError(f"Desteklenmeyen DB_ENGINE: {engine}")
