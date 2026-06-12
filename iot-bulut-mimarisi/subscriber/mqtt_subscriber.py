# mqtt_subscriber.py MQTT Subscriber
# Simülatörün gönderdiği mesajları alır,
# Supabase'e yazar, latency ölçer.

"""

python subscriber/mqtt_subscriber.py

"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json, time, statistics
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
import psycopg2

from config import (
    BROKER_HOST, BROKER_PORT, MQTT_USER, MQTT_PASS,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS,
    UNITS, ALARM_THRESHOLDS
)

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "subscriber_log.txt")
os.makedirs(LOG_DIR, exist_ok=True)

latency_records = []
message_count = db_write_count = alarm_count = 0

# Hem konsola yazdırır hem logs/subscriber_log.txt dosyasına ekler.
def log(line):
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def _ts():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")

# Supabase'e pyscopg2 ile bağlanır.
def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS, sslmode="require"
    )

# Gelen payload dict'inden alanları çekip measurements tablosuna zaman damgalı şekilde INSERT eder.
def write_measurement(conn, d):
    sql = """INSERT INTO measurements
        (plant_code, zone_name, floor_level, sensor_type, value, tds_value, unit, stage, stage_code, growth_day, alarm, measured_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))"""
    with conn.cursor() as cur:
        cur.execute(sql, (
            d.get("plant_code"),
            d.get("zone"),
            d.get("floor_level"),
            d.get("sensor_type"),
            d.get("value"),
            d.get("tds_value"),
            d.get("unit"),
            d.get("stage"),
            d.get("stage_code"),
            d.get("growth_day"),
            d.get("alarm"),
            d.get("timestamp")
        ))
    conn.commit()

# Alarm durumunda alarms tablosuna yazar.
# ALARMS_THRESHOLDS'tan eşik değerlerini alır, aşım yönüne göre "low"/"high" olarak belirler.
def write_alarm(conn, d):
    lo, hi = ALARM_THRESHOLDS.get(d.get("sensor_type",""), (None,None))
    alarm_type = "low" if lo and d["value"] < lo else "high"
    sql = """INSERT INTO alarms
        (plant_code, zone_name, floor_level, sensor_type, value, threshold_lo, threshold_hi, alarm_type, stage, growth_day, triggered_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s))"""
    with conn.cursor() as cur:
        cur.execute(sql, (
            d.get("plant_code"),
            d.get("zone"),
            d.get("floor_level"),
            d.get("sensor_type"),
            d.get("value"),
            lo, hi,
            alarm_type,
            d.get("stage"),
            d.get("growth_day"),
            d.get("timestamp")
        ))
    conn.commit()

# MQTT callback fonksiyonlarını oluşturur.
def make_callbacks(conn):
    # Broker'a bağlanıldığında dikeytarim/# topic'ine abone olur ve "#" sayesinde tüm alt topic'leri dinler.
    def on_connect(client, userdata, flags, rc, props):
        if rc == 0:
            client.subscribe("dikeytarim/#")
            log(f"[{_ts()}] MQTT ✓ DB ✓ | Dinleniyor: dikeytarim/#\n{'─'*60}")
        else:
            log(f"[{_ts()}] MQTT hata: {rc}")
    # Her gelen mesajda çalışır, Alarm topic'lerini filtreler, Latency hesaplar.
    def on_message(client, userdata, msg):
            global message_count, db_write_count, alarm_count
            if "/alarm/" in msg.topic:
                return
            alinma = datetime.now(timezone.utc).timestamp()
            try:
                d = json.loads(msg.payload.decode("utf-8"))
                lat = round((alinma - float(d["timestamp"])) * 1000, 2)
                sensor = d.get("sensor_type", "?").upper()
                deger  = d.get("value", "?")
                birim  = UNITS.get(d.get("sensor_type",""), "")
                alarm  = d.get("alarm", False)
                message_count += 1
                latency_records.append(lat)
                if alarm: alarm_count += 1
                try:
                    write_measurement(conn, d)
                    if alarm: write_alarm(conn, d)
                    db_write_count += 1
                    db_str = "DB ✓"
                except Exception as e:
                    db_str = f"DB ✗"
                alarm_str = " ⚠ ALARM" if alarm else ""
                log(f"[{_ts()}] {sensor:<14} {str(deger):>7} {birim:<8} Lat:{lat:>7.1f}ms {db_str}{alarm_str}")
            except Exception as e:
                log(f"[{_ts()}] Hata: {e}")
    
    # Bağlantı kopunca log yazar.
    def on_disconnect(client, ud, flags, rc, props):
        log(f"[{_ts()}] Bağlantı koptu")

    return on_connect, on_message, on_disconnect

# Sistem durdurulunca toplam mesaj, DB yazılan, alarm sayısı, ortalama ve max latency değerlerini ekrana basar.
def print_summary():
    log(f"\n{'='*60}")
    log(f" Toplam mesaj  : {message_count}")
    log(f" DB yazılan    : {db_write_count}")
    log(f" Alarm sayısı  : {alarm_count}")
    if latency_records:
        log(f"  Ort. latency   : {statistics.mean(latency_records):.1f} ms")
        log(f"  Max latency    : {max(latency_records):.1f} ms")
    log(f"{'='*60}")

# Önce DB bağlantısını dener, başarısız olursa çıkar.
# Sonrasında MQTT client oluşturur, callback'leri bağlar, broker'a bağlanır ve loop_forever() ile sonsuza kadar mesaj dinler.
def main():
    log(f"[{_ts()}] Başlatılıyor...")
    try:
        conn = get_db()
        log(f"[{_ts()}] Supabase bağlantısı kuruldu ✓")
    except Exception as e:
        log(f"[{_ts()}] Db hatası: {e}")
        return
    
    on_connect, on_message, on_disconnect = make_callbacks(conn)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_connect    = on_connect
    client.on_message    = on_message
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