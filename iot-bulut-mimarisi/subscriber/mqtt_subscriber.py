"""MQTT subscriber that validates sensor payloads and writes them to a configured DB."""

from __future__ import annotations

import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (  # noqa: E402
    BROKER_HOST,
    BROKER_PORT,
    DB_ENGINE,
    DB_HOST,
    DB_NAME,
    DB_PASS,
    DB_PORT,
    DB_USER,
    MQTT_PASS,
    MQTT_USER,
    SQLSERVER_CONNECTION_STRING,
    SQLSERVER_DATABASE,
    SQLSERVER_ENCRYPT,
    SQLSERVER_HOST,
    SQLSERVER_PASSWORD,
    SQLSERVER_PORT,
    SQLSERVER_TRUST_CERTIFICATE,
    SQLSERVER_USER,
    UNITS,
)
from subscriber.message_processor import process_message  # noqa: E402
from subscriber.sensor_store import build_sensor_store  # noqa: E402

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "subscriber_log.txt"

latency_records: list[float] = []
message_count = 0
db_write_count = 0
alarm_count = 0


def log(line: str) -> None:
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def get_db(engine: str = DB_ENGINE):
    selected_engine = engine.lower()
    if selected_engine == "postgres":
        import psycopg2

        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            sslmode="require",
        )
    if selected_engine == "sqlserver":
        from mssql_python import connect

        connection_string = SQLSERVER_CONNECTION_STRING or (
            f"Server={SQLSERVER_HOST},{SQLSERVER_PORT};"
            f"Database={SQLSERVER_DATABASE};"
            f"UID={SQLSERVER_USER};PWD={SQLSERVER_PASSWORD};"
            f"Encrypt={SQLSERVER_ENCRYPT};"
            f"TrustServerCertificate={SQLSERVER_TRUST_CERTIFICATE}"
        )
        return connect(connection_string)
    raise ValueError(f"Desteklenmeyen DB_ENGINE: {engine}")


def make_callbacks(store):
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe("dikeytarim/#")
            log(f"[{_ts()}] MQTT OK DB OK | Dinleniyor: dikeytarim/#")
        else:
            log(f"[{_ts()}] MQTT hata: {reason_code}")

    def on_message(client, userdata, message):
        global alarm_count, db_write_count, message_count

        try:
            result = process_message(store, message.topic, message.payload)
            if result is None:
                return

            data = result["data"]
            latency = result["latency_ms"]
            message_count += 1
            db_write_count += 1
            alarm_count += int(result["alarm_written"])
            latency_records.append(latency)

            sensor = data.get("sensor_type", "?").upper()
            value = data.get("value", "?")
            unit = UNITS.get(data.get("sensor_type", ""), "")
            alarm_text = " ALARM" if data.get("alarm") else ""
            log(
                f"[{_ts()}] {sensor:<14} {str(value):>7} {unit:<8} "
                f"Lat:{latency:>7.1f}ms DB OK{alarm_text}"
            )
        except Exception as exc:
            log(f"[{_ts()}] Hata: {exc}")

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        log(f"[{_ts()}] Bağlantı koptu: {reason_code}")

    return on_connect, on_message, on_disconnect


def print_summary() -> None:
    log(f"\n{'=' * 60}")
    log(f" Toplam mesaj  : {message_count}")
    log(f" DB yazılan    : {db_write_count}")
    log(f" Alarm sayısı  : {alarm_count}")
    if latency_records:
        log(f" Ort. latency  : {statistics.mean(latency_records):.1f} ms")
        log(f" Max latency   : {max(latency_records):.1f} ms")
    log("=" * 60)


def main() -> None:
    log(f"[{_ts()}] Başlatılıyor...")
    try:
        conn = get_db()
        store = build_sensor_store(conn, DB_ENGINE)
        log(f"[{_ts()}] {DB_ENGINE} bağlantısı kuruldu")
    except Exception as exc:
        log(f"[{_ts()}] DB hatası: {exc}")
        return

    on_connect, on_message, on_disconnect = make_callbacks(store)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(BROKER_HOST, BROKER_PORT)
        client.loop_forever()
    except KeyboardInterrupt:
        print_summary()
    finally:
        client.disconnect()
        conn.close()


if __name__ == "__main__":
    main()
