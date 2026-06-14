from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from projeuyp.services import (
    SENSOR_COLUMNS,
    STANDARDS,
    DeterministicPredictionProvider,
    FakeSensorDataProvider,
    JoblibPredictionProvider,
    build_prediction_provider,
    build_sensor_provider,
    check_value,
    generate_sensor_data,
    get_phase_data,
)


@pytest.mark.parametrize(
    ("day", "phase_name"),
    [
        (-5, "1. Çimlenme"),
        (0, "1. Çimlenme"),
        (10, "2. Fide Başlangıç"),
        (26, "5. Hızlı Büyüme"),
        (100, "6. Hasat Öncesi"),
    ],
)
def test_get_phase_data_clamps_cycle(day, phase_name):
    assert get_phase_data(day)["evre"] == phase_name


@pytest.mark.parametrize(
    ("value", "expected_text", "expected_color"),
    [
        (5.0, "Düşük", "#FF5252"),
        (5.7, "Yeterli", "#4CAF50"),
        (6.5, "Yüksek", "#FF5252"),
    ],
)
def test_check_value_renders_status(value, expected_text, expected_color):
    result = check_value(value, 5.5, 6.0)
    assert expected_text in result
    assert expected_color in result


def test_generated_sensor_data_is_repeatable_with_seed():
    first = generate_sensor_data(STANDARDS[2], np.random.default_rng(42))
    second = generate_sensor_data(STANDARDS[2], np.random.default_rng(42))

    assert first == second
    assert set(first) == set(SENSOR_COLUMNS)


def test_fake_sensor_provider_returns_phase_midpoints():
    reading = FakeSensorDataProvider().read(STANDARDS[1])
    assert reading["ph"] == 5.9
    assert reading["co2"] == 500.0


def test_provider_factories_reject_unknown_modes():
    with pytest.raises(ValueError, match="PANEL_DATA_MODE"):
        build_sensor_provider("remote")
    with pytest.raises(ValueError, match="PREDICTION_MODE"):
        build_prediction_provider("remote")


def test_deterministic_prediction_provider():
    provider = DeterministicPredictionProvider(9)
    assert provider.predict(FakeSensorDataProvider().read(STANDARDS[1])) == 9


def test_joblib_provider_returns_none_when_model_is_missing(tmp_path):
    provider = JoblibPredictionProvider(tmp_path / "missing.pkl")
    assert provider.predict(FakeSensorDataProvider().read(STANDARDS[1])) is None


def test_joblib_provider_uses_dashboard_feature_order(tmp_path, monkeypatch):
    model_path = tmp_path / "trained_model.pkl"
    model_path.touch()
    model = Mock()
    model.predict.return_value = [14.0]
    load = Mock(return_value=model)
    monkeypatch.setattr("projeuyp.services.joblib.load", load)

    reading = FakeSensorDataProvider().read(STANDARDS[1])
    provider = JoblibPredictionProvider(Path(model_path))

    assert provider.predict(reading) == 14.0
    frame = model.predict.call_args.args[0]
    assert tuple(frame.columns) == SENSOR_COLUMNS
    load.assert_called_once_with(model_path)
