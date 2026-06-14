from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from simulator.sensor_core import Plant, publish
from subscriber.message_processor import process_message


@pytest.mark.integration
def test_sensor_mqtt_subscriber_fake_db_flow(recording_connection):
    measurement = Plant("zone1", 1, 10).measure()[0]
    measurement["alarm"] = False
    mqtt_client = Mock()

    publish(mqtt_client, measurement)
    topic, payload = mqtt_client.publish.call_args.args[:2]
    result = process_message(
        recording_connection,
        topic,
        payload,
        received_at=measurement["timestamp"] + 0.025,
    )

    stored_sql, stored_parameters = recording_connection.statements[0]
    published_data = json.loads(payload)

    assert result["latency_ms"] == pytest.approx(25)
    assert "INSERT INTO measurements" in stored_sql
    assert stored_parameters[0] == published_data["plant_code"]
    assert stored_parameters[3] == published_data["sensor_type"]
    assert stored_parameters[4] == published_data["value"]
    assert recording_connection.commit_count == 1
