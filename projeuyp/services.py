from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np
import pandas as pd

SENSOR_COLUMNS = ("ph", "ec", "temp", "water_temp", "hum", "co2", "light")

STANDARDS = [
    {
        "min": 0,
        "max": 3,
        "evre": "1. Çimlenme",
        "ph": (5.5, 5.8),
        "ec": (0.5, 0.8),
        "temp": (20, 23),
        "water_temp": (20, 20),
        "co2": (300, 400),
        "light": (80, 120),
        "hum": (80, 90),
    },
    {
        "min": 4,
        "max": 10,
        "evre": "2. Fide Başlangıç",
        "ph": (5.8, 6.0),
        "ec": (1.0, 1.2),
        "temp": (20, 22),
        "water_temp": (18, 19),
        "co2": (400, 600),
        "light": (150, 180),
        "hum": (70, 75),
    },
    {
        "min": 11,
        "max": 15,
        "evre": "3. Fide Gelişim",
        "ph": (5.8, 6.2),
        "ec": (1.2, 1.4),
        "temp": (19, 22),
        "water_temp": (18, 20),
        "co2": (600, 800),
        "light": (200, 250),
        "hum": (65, 70),
    },
    {
        "min": 16,
        "max": 25,
        "evre": "4. NFT Adaptasyon",
        "ph": (5.7, 6.1),
        "ec": (1.5, 1.8),
        "temp": (18, 21),
        "water_temp": (19, 19),
        "co2": (800, 1000),
        "light": (250, 300),
        "hum": (60, 65),
    },
    {
        "min": 26,
        "max": 35,
        "evre": "5. Hızlı Büyüme",
        "ph": (5.6, 6.0),
        "ec": (1.8, 2.0),
        "temp": (18, 22),
        "water_temp": (18, 20),
        "co2": (800, 1000),
        "light": (300, 350),
        "hum": (60, 65),
    },
    {
        "min": 36,
        "max": 45,
        "evre": "6. Hasat Öncesi",
        "ph": (5.8, 6.2),
        "ec": (1.2, 1.4),
        "temp": (17, 20),
        "water_temp": (18, 18),
        "co2": (350, 400),
        "light": (200, 200),
        "hum": (55, 60),
    },
]


def get_phase_data(day: int) -> dict:
    """Return the growth phase, clamping days outside the supported range."""
    if day <= STANDARDS[0]["min"]:
        return STANDARDS[0]
    for phase in STANDARDS:
        if phase["min"] <= day <= phase["max"]:
            return phase
    return STANDARDS[-1]


def check_value(value: float, minimum: float, maximum: float) -> str:
    if value < minimum:
        return f"<span style='color:#FF5252; font-weight:bold;'>" f"{value} (Düşük)</span>"
    if value > maximum:
        return f"<span style='color:#FF5252; font-weight:bold;'>" f"{value} (Yüksek)</span>"
    return f"<span style='color:#4CAF50; font-weight:bold;'>" f"{value} (Yeterli)</span>"


def generate_sensor_data(
    ideal: dict, rng: np.random.Generator | None = None
) -> dict[str, float | int]:
    generator = rng or np.random.default_rng()
    return {
        "ph": round(generator.uniform(ideal["ph"][0] - 0.1, ideal["ph"][1] + 0.1), 1),
        "ec": round(generator.uniform(ideal["ec"][0] - 0.1, ideal["ec"][1] + 0.1), 1),
        "temp": round(
            generator.uniform(ideal["temp"][0] - 0.5, ideal["temp"][1] + 0.5),
            1,
        ),
        "water_temp": round(
            generator.uniform(
                ideal["water_temp"][0] - 0.5,
                ideal["water_temp"][1] + 0.5,
            ),
            1,
        ),
        "hum": round(generator.uniform(ideal["hum"][0] - 3, ideal["hum"][1] + 3), 1),
        "co2": int(generator.uniform(ideal["co2"][0] - 30, ideal["co2"][1] + 30)),
        "light": int(generator.uniform(ideal["light"][0] - 10, ideal["light"][1] + 10)),
    }


class SensorDataProvider(Protocol):
    def read(self, ideal: dict) -> dict[str, float | int]:
        """Return one dashboard-compatible sensor reading."""


@dataclass
class GeneratedSensorDataProvider:
    rng: np.random.Generator = field(default_factory=np.random.default_rng)

    def read(self, ideal: dict) -> dict[str, float | int]:
        return generate_sensor_data(ideal, self.rng)


@dataclass(frozen=True)
class FakeSensorDataProvider:
    values: dict[str, float | int] | None = None

    def read(self, ideal: dict) -> dict[str, float | int]:
        if self.values is not None:
            return dict(self.values)
        return {
            sensor: round((ideal[sensor][0] + ideal[sensor][1]) / 2, 1) for sensor in SENSOR_COLUMNS
        }


class PredictionProvider(Protocol):
    def predict(self, sensor_data: dict[str, float | int]) -> float | None:
        """Return estimated days until harvest, or None when unavailable."""


@dataclass(frozen=True)
class DeterministicPredictionProvider:
    remaining_days: float = 12.0

    def predict(self, sensor_data: dict[str, float | int]) -> float:
        return self.remaining_days


@dataclass
class JoblibPredictionProvider:
    model_path: Path
    _model: object | None = field(default=None, init=False, repr=False)

    def predict(self, sensor_data: dict[str, float | int]) -> float | None:
        if not self.model_path.exists():
            return None
        if self._model is None:
            self._model = joblib.load(self.model_path)
        frame = pd.DataFrame([{column: sensor_data[column] for column in SENSOR_COLUMNS}])
        prediction = self._model.predict(frame)
        return float(prediction[0])


def build_sensor_provider(mode: str | None = None) -> SensorDataProvider:
    selected_mode = (mode or os.getenv("PANEL_DATA_MODE", "generated")).lower()
    if selected_mode == "fake":
        return FakeSensorDataProvider()
    if selected_mode == "generated":
        return GeneratedSensorDataProvider()
    raise ValueError(f"Desteklenmeyen PANEL_DATA_MODE: {selected_mode}")


def build_prediction_provider(
    mode: str | None = None,
    model_path: Path | None = None,
) -> PredictionProvider:
    selected_mode = (mode or os.getenv("PREDICTION_MODE", "model")).lower()
    if selected_mode == "fake":
        days = float(os.getenv("FAKE_PREDICTION_DAYS", "12"))
        return DeterministicPredictionProvider(days)
    if selected_mode == "model":
        configured_path = model_path or Path(
            os.getenv(
                "HARVEST_MODEL_PATH",
                str(Path(__file__).resolve().parent / "trained_model.pkl"),
            )
        )
        return JoblibPredictionProvider(configured_path)
    raise ValueError(f"Desteklenmeyen PREDICTION_MODE: {selected_mode}")
