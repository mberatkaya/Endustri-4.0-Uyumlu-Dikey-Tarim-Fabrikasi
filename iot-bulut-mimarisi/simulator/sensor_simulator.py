# sensor_simulator.py Sensör verisi üreten ana program.
# Başlatılınca interaktif menü açar.
# MQTT'ye publish eder.

"""

python simulator/sensor_simulator.py

"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import random
import time
import statistics
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

from config import (
    BROKER_HOST, BROKER_PORT, MQTT_USER, MQTT_PASS,
    GROWTH_STAGES, ALARM_THRESHOLDS, UNITS
)

EC_TO_TDS = 640.0

# Verilen gunun hangi buyume asamasina girdigini dondurur.
def get_stage_by_day(day: int) -> dict:
    for s in GROWTH_STAGES:
        if s["day_start"] <= day <= s["day_end"]:
            return s
    return GROWTH_STAGES[-1]

# Ilgili asama icin normal dagilimla gercekci sensor verisi uretir.
def generate_value(sensor: str, stage: dict) -> float:
    lo, hi, std = stage["sensors"][sensor]
    val = random.gauss((lo + hi) / 2, std)
    bounds = {
        "ph":           (4.0,   8.5),
        "ec":           (0.0,   4.0),
        "temperature":  (10.0,  35.0),
        "humidity":     (30.0, 100.0),
        "co2":          (200.0, 2000.0),
        "light":        (0.0, 500.0),
    }
    lo_h, hi_h = bounds.get(sensor, (-9999, 9999))
    return round(max(lo_h, min(hi_h, val)), 2)

# ALARM_THRESHOLDS'a bakarak degerin alarm sınırlarında olup olmadığını kontrol eder True/False doner.
def is_alarm(sensor: str, value: float) -> bool:
    lo, hi = ALARM_THRESHOLDS.get(sensor, (None, None))
    return lo is not None and (value < lo or value > hi)

# Bitki sinifi
class Plant:
    def __init__(self, zone: str, floor: int, growth_day: int):
        self.zone = zone
        self.floor = floor
        self.growth_day = growth_day
        self.code = f"Z{zone[-1]}-F{floor}"

    def stage(self) -> dict:
        return get_stage_by_day(self.growth_day)
    
    # Tum sensorler icin bir tur olcum yapar generate_value kullanir.
    def measure(self) -> list:
        stage = self.stage()
        ts = datetime.now(timezone.utc).timestamp()
        rows = []
        for sensor in stage["sensors"]:
            value = generate_value(sensor, stage)
            rows.append({
                "plant_code": self.code,
                "zone": self.zone,
                "floor_level": self.floor,
                "sensor_type": sensor,
                "value": value,
                "tds_value": round(value * EC_TO_TDS, 1) if sensor == "ec" else None,
                "unit": UNITS.get(sensor, ""),
                "stage": stage["name"],
                "stage_code": stage["code"],
                "growth_day": self.growth_day,
                "timestamp": ts,
                "alarm": is_alarm(sensor, value),
            })
        return rows
    
# HiveMQ'ya baglanir 
def connect_mqtt() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()

    connected = []
    client.on_connect = lambda cl, ud, fl, rc, pr: connected.append(rc == 0)
    client.connect(BROKER_HOST, BROKER_PORT)
    client.loop_start()

    for _ in range(30):
        if connected:
            break
        time.sleep(0.3)

    if not connected or not connected[0]:
        print("  [HATA] MQTT baglantisi kurulamadi.")
        return None
    
    print(f"  [MQTT] Baglandi -> {BROKER_HOST}")
    return client

def publish(client: mqtt.Client, row: dict):
    topic = f"dikeytarim/{row['zone']}/floor{row['floor_level']}/{row['sensor_type']}"
    client.publish(topic, json.dumps(row, default=str), qos=1)
    if row["alarm"]:
        client.publish(
            f"dikeytarim/alarm/{row['plant_code']}",
            json.dumps(row, default=str),
            qos=2
        )

# Konsola tek satır cikti basar
def print_row(row: dict):
    alarm_str = " <<<ALARM!" if row['alarm'] else ""
    tds_str = f" TDS:{row['tds_value']}ppm" if row.get("tds_value") else ""
    print(
        f" [{row['plant_code']}] "
        f"{row['sensor_type']:<14} "
        f"{row['value']:>7.2f} {row['unit']:<8} "
        f"Gun:{row['growth_day']:>2} {row['stage_code']}"
        f"{tds_str}{alarm_str}"
    )

def print_plant_table(plants: list):
    print()
    print(f"  {'Bitki':<10} {'Zone':<8} {'Raf':<5} {'Gun':>5}  Asama")
    print(f"  {'─'*55}")
    for p in plants:
        s = p.stage()
        print(f"  {p.code:<10} {p.zone:<8} {p.floor:<5} {p.growth_day:>5} {s['name']} ({s['code']})")
    print(f"  {'─'*55}")
    print(f"  Toplam: {len(plants)} bitki¨\n")

# Ek menuler kullanicidan secim alir, yanlis giriste tekrar sorar, bos giriste varsayilani alir.    
def ask_int(prompt: str, lo: int, hi: int, default: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return default
        if raw.isdigit() and lo <- int(raw) <= hi:
            return int(raw)
        print(f"  Lutfen {lo} ile {hi} arasinda bir sayi girin.")

def ask_choice(prompt: str, choices: list, default: str) -> str:
    choices_lower = [c.lower() for c in choices]
    while True:
        raw = input(prompt).strip().lower()
        if raw == "":
            return default.lower()
        if raw in choices_lower:
            return raw
        print(f"  Gecersiz secim. Secenekler: {choices}")

def separator(title: str = ""):
    if title:
        print(f"\n── {title} {'─' * (50 - len(title))}")
    else:
        print()

def step1_factory() -> tuple:
    separator("ADIM 1 - Fabrika Yapılandırması")
    n_zones = ask_int(" Kac zone? [1-5, varsayilan 3]: ", 1, 5, 3)
    n_floors = ask_int(" Zone basina kac raf? [1-8, varsayilan 4]: ", 1, 8, 4)
    print(f"\n {n_zones} zone x {n_floors} raf = {n_zones * n_floors} bitki yuvası")
    return n_zones, n_floors

def step2_growth_days(n_zones: int, n_floors: int) -> list:
    separator("ADIM 2 - Büyüme Günü Dağılımı")
    print("  [R] Rastgele - her bitki farkli bir gunden baslar (1-40)")
    print("  [S] Senkron - tum bitkiler ayni gunden baslar")
    print("  [M] Manuel - her bitkiye ayri ayri gun girilir")
    mode = ask_choice("  Secim [R/S/M, varsayilan R]: ", ["r", "s", "m"], "r")

    plants = []
    zone_names = [f"zone{i+1}" for i in range(n_zones)]

    if mode == "r":
        for z in zone_names:
            for f in range(1, n_floors + 1):
                plants.append(Plant(z, f, random.randint(1, 40)))
    
    elif mode == "s":
        gun = ask_int("  Tum bitkiler kacinci gunden baslasin? [1-40, varsayilan 20]: ", 1, 40, 20)
        for z in zone_names:
            for f in range(1, n_floors + 1):
                plants.append(Plant(z, f, gun))
    
    elif mode == "m":
        print("\n  Her bitki icin buyume gunu girilecek (1-40):")
        for z in zone_names:
            for f in range(1, n_floors + 1):
                code = f"Z{z[-1]}-F{f}"
                gun = ask_int(f"  {code} buyume gunu: ", 1, 40, 20)
                plants.append(Plant(z, f, gun))

    print_plant_table(plants)

    if mode == "r":
        duz = ask_choice(
            " Tabloyu duzenlemek ister misiniz? [E/H, varsayilan H]: ",
            ["e", "h"], "h"
        )
        if duz == "e":
            plants = edit_table(plants)

    return plants

def edit_table(plants: list) -> list:
    while True:
        raw = input("  Duzenlenecek bitki kodu (ornek Z1-F2) veya [Enter] bitirmek icin: ").strip().upper()
        if raw == "":
            break
        match = [p for p in plants if p.code == raw]
        if not match:
            print(f"    '{raw}' bulunamadi. Gecerli kodlar: {[p.code for p in plants]}")
            continue
        p = match[0]
        gun = ask_int(f"  {p.code} icin yeni gun [1-40]: ", 1, 40, p.growth_day)
        p.growth_day = gun
        print(f"  {p.code} -> Gun {gun} ({p.stage()['name']}) olarak guncellendi.")
    print_plant_table(plants)
    return plants

def step3_speed() -> float:
    separator("ADIM 3 - Gönderim Hızı")
    print("  [1] Normal - 5 saniyede bir")
    print("  [2] Hizli - 2 saniyede bir")
    print("  [3] Stres - 0.5 saniyede bir")
    print("  [4] Manuel - istedigin degeri gir")
    sec = ask_choice("  Secim [1/2/3/4, varsayilan 1]: ", ["1", "2", "3", "4"], "1")
    if sec == "1": return 5.0
    if sec == "2": return 2.0
    if sec == "3": return 0.5

    while True:
        raw = input("  Aralik (saniye, ornek 1.5): ").strip()
        try:
            val = float(raw)
            if val > 0:
                return val
        except ValueError:
            pass
        print("  Gecerli bir sayi girin.")

def step4_target() -> str:
    separator("ADIM 4 - Çıktı Hedefi")
    print("  [A] Yalnizca konsol - MQTT yok, hizli test icin")
    print("  [B] MQTT broker - HiveMQ Cloud'a gonder")
    print("  [C] MQTT + Supabase - broker ve veritabanina yaz")
    return ask_choice("  Secim [A/B/C, varsayilan C]: ", ["a", "b", "c"], "c")

# Asıl simulasyon dongusu baglantilari kurar, sonsuz while dongusune girer durduruluncaya kadar 
# tum bitkiler icin measure() cagirir, publish eder, konsola yazar, latency kaydeder
def run(plants: list, interval: float, target:str):
    client = None
    if target in ["b", "c"]:
        separator("Bağlantılar kuruluyor")
        client = connect_mqtt()
        if client is None:
            print("  MQTT baglantisi basarisiz, konsol moduna geciliyor.")
            target = "a"

    separator()
    print(f"  Simulasyon basliyor")
    print(f"  Bitki sayisi : {len(plants)}")
    print(f"  Gonderim araligi: {interval}s")
    hedef_str = {"a": "Konsol", "b": "MQTT", "c": "MQTT + Supabase"}
    print(f"  Cikti hedefi : {hedef_str.get(target, '?')}")
    print(f"  Durdurmak icin : Ctrl+C")
    print(f"  {'─'*50}")

    toplam_mesaj = 0
    toplam_alarm = 0
    latency_kayit = []

    try:
        while True:
            ts_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"\n[{ts_str}]  {len(plants)} bitki olcum yapiliyor...")

            for plant in plants:
                for row in plant.measure():
                    t0 = time.time()

                    if client:
                        publish(client, row)

                    lat = round((time.time() - t0) * 1000, 1)
                    latency_kayit.append(lat)
                    toplam_mesaj += 1
                    if row["alarm"]:
                        toplam_alarm += 1

                    print_row(row)

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n  {'═'*50}")
        print(f"  OTURUM OZETI")
        print(f"  {'═'*50}")
        print(f"  Toplam mesaj  : {toplam_mesaj}")
        print(f"  Toplam alarm  : {toplam_alarm}")
        if latency_kayit:
            print(f"  Min latency   : {min(latency_kayit):.1f} ms")
            print(f"  Max latency   : {max(latency_kayit):.1f} ms")
            print(f"  Ort. latency  : {statistics.mean(latency_kayit):.1f} ms")
        print(f"  {'═'*50}")

    finally:
        if client:
            client.loop_stop()
            client.disconnect()

def main():
    print("\n" + "=" * 55)
    print("  EKO-URETIM Marul Sensor Simulatoru")
    print("  Gorkem Furkan Caglayan | P8 Grubu")
    print("=" * 55)

    n_zones, n_floors = step1_factory()
    plants            = step2_growth_days(n_zones, n_floors)
    interval          = step3_speed()
    target            = step4_target()

    run(plants, interval, target)


if __name__ == "__main__":
    main()