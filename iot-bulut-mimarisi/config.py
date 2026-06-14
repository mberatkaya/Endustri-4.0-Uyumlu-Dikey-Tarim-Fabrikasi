# config.py Merkezi Ayar Dosyası
# Tüm ayarlar burada. Broker bilgileri,
# DB bilgileri, alarm eşikleri, büyüme aşamaları.
# Diğer tüm dosyalar buradan import eder.

import os

# HiveMQ Cloud bağlantı bilgileri
BROKER_HOST = os.getenv("MQTT_HOST", "your-cluster.s1.eu.hivemq.cloud")
BROKER_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USER", "your_username")
MQTT_PASS = os.getenv("MQTT_PASS", "your_password")

# Sistemdeki zone'lar fiziksel bölümler (her biri bir raf/bölümü temsil eder)
ZONES = ["zone1", "zone2", "zone3"]

# MQTT topic şablonu. Topic şablonları MQTT mesajlarının hangi adrese gideceğini belirler.
TOPIC_SENSOR = "dikeytarim/{zone}/{sensor}"
TOPIC_ALARM = "dikeytarim/alarm/{zone}"
TOPIC_ALL = "dikeytarim/#"

# Alarm eşikleri - bu sınırların dışına çıkılırsa alarm üretilir.
ALARM_THRESHOLDS = {
    "temperature": (18.0, 26.0),
    "humidity": (55.0, 85.0),
    "ph": (5.4, 6.5),
    "ec": (0.5, 2.5),
    "co2": (350.0, 1200.0),
    "light": (70.0, 350.0),
}

# Her sensör için ölçüm birimleri.
UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "ph": "pH",
    "ec": "mS/cm",
    "co2": "ppm",
    "light": "µmol",
}

# Marul bitkisinin büyüme aşamaları
# Kaynak: marulun_zamana_bağlı_üretim_parametreleri.ods
# Her sensör için (ideal_min, ideal_max, std_sapma)
# Simulator bu üçlüyü kullanarak Gauss dağılımıyla değer üretir.
GROWTH_STAGES = [
    {
        "stage_id": 1,
        "name": "Çimlenme",
        "code": "E2",
        "day_start": 1,
        "day_end": 3,
        "sensors": {
            "ph": (5.5, 5.8, 0.08),
            "ec": (0.5, 0.8, 0.05),
            "temperature": (20.0, 23.0, 0.4),
            "humidity": (80.0, 90.0, 1.5),
            "co2": (350.0, 420.0, 15.0),
            "light": (80.0, 120.0, 8.0),
        },
        "critical_sensor": "light",
        "risk": "Düşük ışık → zayıf çıkış",
    },
    {
        "stage_id": 2,
        "name": "Fide Başlangıç",
        "code": "E3",
        "day_start": 4,
        "day_end": 10,
        "sensors": {
            "ph": (5.8, 6.0, 0.08),
            "ec": (1.0, 1.2, 0.06),
            "temperature": (20.0, 22.0, 0.4),
            "humidity": (70.0, 75.0, 1.2),
            "co2": (550.0, 650.0, 20.0),
            "light": (150.0, 180.0, 8.0),
        },
        "critical_sensor": "humidity",
        "risk": "Yüksek nem → fungal risk",
    },
    {
        "stage_id": 3,
        "name": "Fide Gelişim",
        "code": "E4",
        "day_start": 11,
        "day_end": 15,
        "sensors": {
            "ph": (5.8, 6.2, 0.10),
            "ec": (1.2, 1.4, 0.07),
            "temperature": (19.0, 22.0, 0.5),
            "humidity": (65.0, 70.0, 1.2),
            "co2": (750.0, 850.0, 25.0),
            "light": (200.0, 250.0, 10.0),
        },
        "critical_sensor": "ph",
        "risk": "pH drift → besin alımı bozulur",
    },
    {
        "stage_id": 4,
        "name": "NFT Adaptasyon",
        "code": "E5",
        "day_start": 16,
        "day_end": 25,
        "sensors": {
            "ph": (5.7, 6.1, 0.10),
            "ec": (1.5, 1.8, 0.08),
            "temperature": (18.0, 21.0, 0.5),
            "humidity": (60.0, 65.0, 1.2),
            "co2": (950.0, 1050.0, 30.0),
            "light": (250.0, 300.0, 10.0),
        },
        "critical_sensor": "co2",
        "risk": "CO₂ düşük → fotosentez azalır",
    },
    {
        "stage_id": 5,
        "name": "Hızlı Büyüme",
        "code": "E6",
        "day_start": 26,
        "day_end": 35,
        "sensors": {
            "ph": (5.6, 6.0, 0.10),
            "ec": (1.8, 2.0, 0.08),
            "temperature": (18.0, 22.0, 0.5),
            "humidity": (60.0, 65.0, 1.2),
            "co2": (950.0, 1050.0, 30.0),
            "light": (290.0, 310.0, 8.0),
        },
        "critical_sensor": "temperature",
        "risk": "Yüksek sıcaklık → acılaşma",
    },
    {
        "stage_id": 6,
        "name": "Hasat Öncesi",
        "code": "E7",
        "day_start": 36,
        "day_end": 40,
        "sensors": {
            "ph": (5.8, 6.2, 0.08),
            "ec": (1.2, 1.4, 0.06),
            "temperature": (17.0, 20.0, 0.4),
            "humidity": (55.0, 60.0, 1.2),
            "co2": (370.0, 430.0, 15.0),
            "light": (190.0, 210.0, 8.0),
        },
        "critical_sensor": "ec",
        "risk": "Tuz birikimi → EC düşür veya Flush",
    },
]

# Veritabanı backend'i. Varsayılan mevcut Supabase/PostgreSQL akışıdır.
DB_ENGINE = os.getenv("DB_ENGINE", "postgres").lower()

# Supabase/PostgreSQL bağlantı bilgileri.
DB_HOST = os.getenv("DB_HOST", "aws-0-eu-west-1.pooler.supabase.com")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres.your_project_id")
DB_PASS = os.getenv("DB_PASS", "your_db_password")

# Microsoft SQL Server bağlantı bilgileri.
SQLSERVER_CONNECTION_STRING = os.getenv("SQLSERVER_CONNECTION_STRING", "")
SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "localhost")
SQLSERVER_PORT = int(os.getenv("SQLSERVER_PORT", "1433"))
SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE", "DikeyTarimDB")
SQLSERVER_USER = os.getenv("SQLSERVER_USER", "sa")
SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "your_sqlserver_password")
SQLSERVER_ENCRYPT = os.getenv("SQLSERVER_ENCRYPT", "yes")
SQLSERVER_TRUST_CERTIFICATE = os.getenv("SQLSERVER_TRUST_CERTIFICATE", "no")
