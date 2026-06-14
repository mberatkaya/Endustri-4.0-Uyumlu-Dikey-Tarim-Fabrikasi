from __future__ import annotations

import json

import pytest
from subscriber.message_processor import (
    process_message,
    validate_payload,
    write_alarm,
    write_measurement,
)


def test_validate_payload_rejects_missing_fields(sample_sensor_payload):
    sample_sensor_payload.pop("zone")
    with pytest.raises(ValueError, match="Eksik sensör"):
        validate_payload(sample_sensor_payload)


def test_validate_payload_rejects_non_numeric_value(sample_sensor_payload):
    sample_sensor_payload["value"] = "5.8"
    with pytest.raises(ValueError, match="sayısal"):
        validate_payload(sample_sensor_payload)


def test_write_measurement_uses_measurements_table(
    recording_connection,
    sample_sensor_payload,
):
    write_measurement(recording_connection, sample_sensor_payload)

    assert recording_connection.commit_count == 1
    sql, parameters = recording_connection.statements[0]
    assert "INSERT INTO measurements" in sql
    assert parameters[0] == "Z1-F1"
    assert parameters[4] == 5.8


def test_write_alarm_classifies_low_threshold(
    recording_connection,
    sample_sensor_payload,
):
    sample_sensor_payload["value"] = 4.5
    sample_sensor_payload["alarm"] = True
    write_alarm(recording_connection, sample_sensor_payload)

    sql, parameters = recording_connection.statements[0]
    assert "INSERT INTO alarms" in sql
    assert parameters[7] == "low"


def test_process_message_writes_measurement(
    recording_connection,
    sample_sensor_payload,
):
    result = process_message(
        recording_connection,
        "dikeytarim/zone1/floor1/ph",
        json.dumps(sample_sensor_payload).encode(),
        received_at=sample_sensor_payload["timestamp"] + 0.05,
    )

    assert result["latency_ms"] == pytest.approx(50)
    assert result["alarm_written"] is False
    assert recording_connection.commit_count == 1


def test_process_message_writes_alarm(
    recording_connection,
    sample_sensor_payload,
):
    sample_sensor_payload["alarm"] = True
    sample_sensor_payload["value"] = 7.0
    result = process_message(
        recording_connection,
        "dikeytarim/zone1/floor1/ph",
        json.dumps(sample_sensor_payload),
        received_at=sample_sensor_payload["timestamp"],
    )

    assert result["alarm_written"] is True
    assert recording_connection.commit_count == 2
    assert len(recording_connection.statements) == 2


def test_process_message_ignores_alarm_topic(
    recording_connection,
    sample_sensor_payload,
):
    result = process_message(
        recording_connection,
        "dikeytarim/alarm/Z1-F1",
        json.dumps(sample_sensor_payload),
    )
    assert result is None
    assert recording_connection.statements == []
