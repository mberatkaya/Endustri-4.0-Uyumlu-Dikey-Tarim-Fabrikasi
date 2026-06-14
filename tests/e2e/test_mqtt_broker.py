from __future__ import annotations

import os
import threading
import uuid

import paho.mqtt.client as mqtt
import pytest


@pytest.mark.e2e
def test_temporary_mqtt_broker_round_trip():
    host = os.getenv("MQTT_TEST_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_TEST_PORT", "1883"))
    topic = f"dikeytarim/ci/{uuid.uuid4()}"
    received = []
    delivered = threading.Event()
    subscribed = threading.Event()

    subscriber = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_message(client, userdata, message):
        received.append(message.payload.decode())
        delivered.set()

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(topic, qos=1)

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        subscribed.set()

    subscriber.on_connect = on_connect
    subscriber.on_message = on_message
    subscriber.on_subscribe = on_subscribe
    subscriber.connect(host, port)
    subscriber.loop_start()
    publisher.connect(host, port)
    publisher.loop_start()

    try:
        assert subscribed.wait(timeout=5)
        publisher.publish(topic, "sensor-ok", qos=1).wait_for_publish()
        assert delivered.wait(timeout=5)
        assert received == ["sensor-ok"]
    finally:
        publisher.loop_stop()
        publisher.disconnect()
        subscriber.loop_stop()
        subscriber.disconnect()
