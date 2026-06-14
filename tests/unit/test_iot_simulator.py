from __future__ import annotations

from unittest.mock import Mock

import pytest
from simulator.sensor_core import Plant, generate_value, get_stage_by_day, is_alarm, publish
from simulator.sensor_simulator import ask_int


@pytest.mark.parametrize(
    ("day", "expected_code"),
    [
        (-1, "E2"),
        (0, "E2"),
        (1, "E2"),
        (10, "E3"),
        (40, "E7"),
        (100, "E7"),
    ],
)
def test_get_stage_by_day_clamps_supported_cycle(day, expected_code):
    assert get_stage_by_day(day)["code"] == expected_code


@pytest.mark.parametrize(
    ("sensor", "minimum", "maximum"),
    [
        ("ph", 4.0, 8.5),
        ("ec", 0.0, 4.0),
        ("temperature", 10.0, 35.0),
        ("humidity", 30.0, 100.0),
        ("co2", 200.0, 2000.0),
        ("light", 0.0, 500.0),
    ],
)
def test_generate_value_respects_physical_bounds(sensor, minimum, maximum):
    stage = get_stage_by_day(10)
    values = [generate_value(sensor, stage) for _ in range(100)]
    assert all(minimum <= value <= maximum for value in values)


@pytest.mark.parametrize(
    ("sensor", "value", "expected"),
    [
        ("ph", 4.5, True),
        ("ph", 6.0, False),
        ("temperature", 30.0, True),
        ("unknown", 10.0, False),
    ],
)
def test_alarm_thresholds(sensor, value, expected):
    assert is_alarm(sensor, value) is expected


def test_plant_measurement_contains_complete_sensor_contract():
    measurements = Plant("zone2", 3, 20).measure()

    assert {row["sensor_type"] for row in measurements} == {
        "ph",
        "ec",
        "temperature",
        "humidity",
        "co2",
        "light",
    }
    assert all(row["plant_code"] == "Z2-F3" for row in measurements)
    assert all(row["stage_code"] == "E5" for row in measurements)
    assert all(isinstance(row["alarm"], bool) for row in measurements)

    ec_row = next(row for row in measurements if row["sensor_type"] == "ec")
    assert ec_row["tds_value"] == pytest.approx(ec_row["value"] * 640, abs=0.1)


def test_publish_uses_sensor_and_alarm_topics():
    client = Mock()
    row = Plant("zone1", 1, 10).measure()[0]
    row["alarm"] = True

    publish(client, row)

    assert client.publish.call_count == 2
    sensor_call, alarm_call = client.publish.call_args_list
    assert sensor_call.args[0] == f"dikeytarim/zone1/floor1/{row['sensor_type']}"
    assert sensor_call.kwargs["qos"] == 1
    assert alarm_call.args[0] == "dikeytarim/alarm/Z1-F1"
    assert alarm_call.kwargs["qos"] == 2


def test_ask_int_retries_until_value_is_in_range(monkeypatch):
    answers = iter(["abc", "0", "6", "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert ask_int("Sayı: ", 1, 5, 3) == 4


def test_ask_int_accepts_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    assert ask_int("Sayı: ", 1, 5, 3) == 3
