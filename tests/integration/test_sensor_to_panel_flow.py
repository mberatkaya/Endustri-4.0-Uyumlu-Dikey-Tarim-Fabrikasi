from __future__ import annotations

import pytest

from projeuyp.services import STANDARDS, DeterministicPredictionProvider, FakeSensorDataProvider


@pytest.mark.integration
def test_fake_sensor_to_prediction_contract():
    reading = FakeSensorDataProvider().read(STANDARDS[3])
    prediction = DeterministicPredictionProvider(11).predict(reading)

    assert set(reading) == {
        "ph",
        "ec",
        "temp",
        "water_temp",
        "hum",
        "co2",
        "light",
    }
    assert prediction == 11
