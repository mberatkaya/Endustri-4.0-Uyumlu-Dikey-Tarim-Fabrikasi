from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from subscriber.message_processor import process_message, validate_payload


def test_validate_payload_rejects_missing_fields(sample_sensor_payload):
    sample_sensor_payload.pop("zone")
    with pytest.raises(ValueError, match="Eksik sensör"):
        validate_payload(sample_sensor_payload)


def test_validate_payload_rejects_non_numeric_value(sample_sensor_payload):
    sample_sensor_payload["value"] = "5.8"
    with pytest.raises(ValueError, match="sayısal"):
        validate_payload(sample_sensor_payload)


def test_validate_payload_rejects_non_boolean_alarm(sample_sensor_payload):
    sample_sensor_payload["alarm"] = 1
    with pytest.raises(ValueError, match="boolean"):
        validate_payload(sample_sensor_payload)


def test_process_message_writes_measurement(
    sample_sensor_payload,
):
    store = Mock()
    result = process_message(
        store,
        "dikeytarim/zone1/floor1/ph",
        json.dumps(sample_sensor_payload).encode(),
        received_at=sample_sensor_payload["timestamp"] + 0.05,
    )

    assert result["latency_ms"] == pytest.approx(50)
    assert result["alarm_written"] is False
    store.write.assert_called_once_with(sample_sensor_payload)


def test_process_message_writes_alarm(
    sample_sensor_payload,
):
    store = Mock()
    sample_sensor_payload["alarm"] = True
    sample_sensor_payload["value"] = 7.0
    result = process_message(
        store,
        "dikeytarim/zone1/floor1/ph",
        json.dumps(sample_sensor_payload),
        received_at=sample_sensor_payload["timestamp"],
    )

    assert result["alarm_written"] is True
    store.write.assert_called_once_with(sample_sensor_payload)


def test_process_message_ignores_alarm_topic(
    sample_sensor_payload,
):
    store = Mock()
    result = process_message(
        store,
        "dikeytarim/alarm/Z1-F1",
        json.dumps(sample_sensor_payload),
    )
    assert result is None
    store.write.assert_not_called()
