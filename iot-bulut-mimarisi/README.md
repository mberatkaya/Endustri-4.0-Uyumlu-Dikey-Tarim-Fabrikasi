# IoT Bulut Mimarisi

Bu klasor, dikey tarim verileriyle IoT sensor simulasyonu ve bulut altyapisi
calismalarini icerir. Marul bitkisinin 6 buyume asamasina ozgu sensor verisi,
HiveMQ Cloud MQTT broker uzerinden secilen PostgreSQL veya SQL Server backend'ine
iletilir.

---

## Sistem Mimarisi

```
Sensor Simulatoru -> HiveMQ Cloud (MQTT/TLS) -> Subscriber -> SensorStore
                                                          -> PostgreSQL
                                                          -> SQL Server
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
pip install -r requirements.txt
```

SQL Server kullanilacaksa:

```bash
pip install -r requirements-sqlserver.txt
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

SQL Server icin `DB_ENGINE=sqlserver` secilir. Tam baglanti dizesi verilebilir:

```bash
export DB_ENGINE="sqlserver"
export SQLSERVER_CONNECTION_STRING="Server=localhost,1433;Database=DikeyTarimDB;UID=sa;PWD=secret;Encrypt=yes;TrustServerCertificate=yes"
```

Alternatif olarak `SQLSERVER_HOST`, `SQLSERVER_PORT`, `SQLSERVER_DATABASE`,
`SQLSERVER_USER`, `SQLSERVER_PASSWORD`, `SQLSERVER_ENCRYPT` ve
`SQLSERVER_TRUST_CERTIFICATE` degiskenleri kullanilir.

Bos SQL Server kurulumu icin depo kokundeki `DikeyTarimSQL/01_Veritabani.sql` -
`12_Trigger.sql` dosyalari numara sirasiyla calistirilir. `13` ve `14` numarali
dosyalar rapor/inceleme sorgularidir.

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

Her gelen mesaji ekrana basar, latency hesaplar ve secilen veritabanina yazar:

```
[13:19:19] PH            5.85 pH       Lat:   79.0ms  DB ✓
[13:19:20] EC            1.28 mS/cm    Lat:  300.6ms  DB ✓
[13:19:20] TEMPERATURE  20.81 °C       Lat:  515.2ms  DB ✓
```
