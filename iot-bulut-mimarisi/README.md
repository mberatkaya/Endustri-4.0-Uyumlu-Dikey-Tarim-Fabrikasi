# IoT Bulut Mimarisi

Bu klasor, dikey tarim verileriyle iot sensor simülasyonu ve bulut altyapisi calismalarini icerir.
Marul bitkisinin 6 büyüme aşamasına özgü sensör verisi simüle edilerek HiveMQ Cloud MQTT broker üzerinden Supabase PostgreSQL bulut veritabanına iletilmektedir.

---

## Sistem Mimarisi

```
Sensör Simülatörü  →  HiveMQ Cloud (MQTT/TLS)  →  Subscriber  →  Supabase PostgreSQL
```

## Klasör Yapısı

```
uyp-p8-iot/
├── config.py                   ← Merkezi ayar dosyası
├── simulator/
│   └── sensor_simulator.py     ← İnteraktif menülü sensör simülatörü
├── subscriber/
│   └── mqtt_subscriber.py      ← MQTT dinleyici + Supabase DB yazıcı
└── logs/                       ← Test çıktıları
```

---

## Kurulum

```bash
pip install paho-mqtt psycopg2-binary
```

Bağlantı bilgilerini ortam değişkenleriyle verin:

```bash
export MQTT_HOST="your-cluster.s1.eu.hivemq.cloud"
export MQTT_PORT="8883"
export MQTT_USER="your_username"
export MQTT_PASS="your_password"

export DB_HOST="aws-0-eu-west-1.pooler.supabase.com"
export DB_PORT="5432"
export DB_NAME="postgres"
export DB_USER="postgres.your_project_id"
export DB_PASS="your_db_password"
```

---

## Kullanım

### Sensör Simülatörü

```bash
python simulator/sensor_simulator.py
```

Başlatılınca 4 adımlı interaktif menü açılır:

```
── ADIM 1: Fabrika Yapılandırması ──
  Kaç zone? [1-5, varsayılan 3]:
  Zone başına kaç raf? [1-8, varsayılan 4]:
  → 3 zone × 4 raf = 12 bitki yuvası

── ADIM 2: Büyüme Günü Dağılımı ──
  [R] Rastgele   [S] Senkron   [M] Manuel

── ADIM 3: Gönderim Hızı ──
  [1] Normal 5s  [2] Hızlı 2s  [3] Stres 0.5s  [4] Manuel

── ADIM 4: Çıktı Hedefi ──
  [A] Konsol     [B] MQTT      [C] MQTT + Supabase
```

### MQTT Subscriber (ayrı terminalde)

```bash
python subscriber/mqtt_subscriber.py
```

Her gelen mesajı ekrana basar, latency hesaplar ve Supabase'e yazar:

```
[13:19:19] PH            5.85 pH       Lat:   79.0ms  DB ✓
[13:19:20] EC            1.28 mS/cm    Lat:  300.6ms  DB ✓
[13:19:20] TEMPERATURE  20.81 °C       Lat:  515.2ms  DB ✓
```
