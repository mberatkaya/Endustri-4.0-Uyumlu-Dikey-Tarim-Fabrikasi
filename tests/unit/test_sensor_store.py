from __future__ import annotations

from datetime import datetime

import pytest
from subscriber.sensor_store import PostgresSensorStore, SqlServerSensorStore, build_sensor_store


def test_postgres_store_writes_measurement_in_one_transaction(
    recording_connection,
    sample_sensor_payload,
):
    PostgresSensorStore(recording_connection).write(sample_sensor_payload)

    assert recording_connection.commit_count == 1
    assert recording_connection.rollback_count == 0
    assert recording_connection.cursor_close_count == 1
    sql, parameters = recording_connection.statements[0]
    assert "INSERT INTO measurements" in sql
    assert parameters[0] == "Z1-F1"
    assert parameters[3] == "ph"
    assert parameters[4] == 5.8


def test_postgres_store_writes_alarm_in_same_transaction(
    recording_connection,
    sample_sensor_payload,
):
    sample_sensor_payload["value"] = 4.5
    sample_sensor_payload["alarm"] = True

    PostgresSensorStore(recording_connection).write(sample_sensor_payload)

    assert recording_connection.commit_count == 1
    assert len(recording_connection.statements) == 2
    alarm_sql, alarm_parameters = recording_connection.statements[1]
    assert "INSERT INTO alarms" in alarm_sql
    assert alarm_parameters[7] == "low"


def test_postgres_store_classifies_high_alarm(
    recording_connection,
    sample_sensor_payload,
):
    sample_sensor_payload["value"] = 7.0
    sample_sensor_payload["alarm"] = True

    PostgresSensorStore(recording_connection).write(sample_sensor_payload)

    assert recording_connection.statements[1][1][7] == "high"


def test_postgres_store_rolls_back_failed_transaction(
    recording_connection,
    sample_sensor_payload,
):
    recording_connection.fail_on_execute = True

    with pytest.raises(RuntimeError, match="Kayit hatasi"):
        PostgresSensorStore(recording_connection).write(sample_sensor_payload)

    assert recording_connection.commit_count == 0
    assert recording_connection.rollback_count == 1
    assert recording_connection.cursor_close_count == 1


def test_sqlserver_store_calls_normalized_sensor_procedure(
    recording_connection,
    sample_sensor_payload,
):
    SqlServerSensorStore(recording_connection).write(sample_sensor_payload)

    assert recording_connection.commit_count == 1
    assert recording_connection.rollback_count == 0
    sql, parameters = recording_connection.statements[0]
    assert "EXEC dbo.sp_SensorVerisiEkle" in sql
    assert sql.count("?") == 10
    assert parameters[0] == "Z1-F1"
    assert isinstance(parameters[1], datetime)
    assert parameters[2] == "ph"
    assert parameters[3] == 5.8
    assert parameters[9] is False


def test_sqlserver_store_relies_on_trigger_for_alarm(
    recording_connection,
    sample_sensor_payload,
):
    sample_sensor_payload["alarm"] = True

    SqlServerSensorStore(recording_connection).write(sample_sensor_payload)

    assert len(recording_connection.statements) == 1
    assert recording_connection.statements[0][1][9] is True
    assert recording_connection.commit_count == 1


def test_sqlserver_store_rolls_back_failed_procedure(
    recording_connection,
    sample_sensor_payload,
):
    recording_connection.fail_on_execute = True

    with pytest.raises(RuntimeError, match="Kayit hatasi"):
        SqlServerSensorStore(recording_connection).write(sample_sensor_payload)

    assert recording_connection.commit_count == 0
    assert recording_connection.rollback_count == 1


@pytest.mark.parametrize(
    ("engine", "expected_type"),
    [
        ("postgres", PostgresSensorStore),
        ("sqlserver", SqlServerSensorStore),
    ],
)
def test_build_sensor_store_selects_backend(recording_connection, engine, expected_type):
    assert isinstance(build_sensor_store(recording_connection, engine), expected_type)


def test_build_sensor_store_rejects_unknown_backend(recording_connection):
    with pytest.raises(ValueError, match="DB_ENGINE"):
        build_sensor_store(recording_connection, "sqlite")
