from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for source_root in (
    PROJECT_ROOT,
    PROJECT_ROOT / "iot-bulut-mimarisi",
    PROJECT_ROOT / "XGBoost-Hasat-Tahmin-Modeli",
    PROJECT_ROOT / "Görüntü İşleme" / "src",
):
    sys.path.insert(0, str(source_root))


class RecordingCursor:
    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql: str, parameters: tuple) -> None:
        if self.connection.fail_on_execute:
            raise RuntimeError("Kayit hatasi")
        self.connection.statements.append((sql, parameters))

    def close(self) -> None:
        self.connection.cursor_close_count += 1


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self.cursor_close_count = 0
        self.fail_on_execute = False

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


@pytest.fixture
def recording_connection() -> RecordingConnection:
    return RecordingConnection()


@pytest.fixture
def sample_sensor_payload() -> dict:
    return {
        "plant_code": "Z1-F1",
        "zone": "zone1",
        "floor_level": 1,
        "sensor_type": "ph",
        "value": 5.8,
        "tds_value": None,
        "unit": "pH",
        "stage": "Fide Başlangıç",
        "stage_code": "E3",
        "growth_day": 10,
        "timestamp": 1_700_000_000.0,
        "alarm": False,
    }
