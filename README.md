# Endüstri 4.0 Uyumlu Dikey Tarım Fabrikası

[![CI](https://github.com/mberatkaya/Endustri-4.0-Uyumlu-Dikey-Tarim-Fabrikasi/actions/workflows/ci.yml/badge.svg)](https://github.com/mberatkaya/Endustri-4.0-Uyumlu-Dikey-Tarim-Fabrikasi/actions/workflows/ci.yml)

Beykent Üniversitesi bitirme projesi kapsamında geliştirilen dikey tarım sistemi; sensör
simülasyonu, MQTT veri aktarımı, seçilebilir PostgreSQL/Supabase veya SQL Server yazımı,
XGBoost hasat tahmini, YOLO tabanlı görüntü analizi ve Streamlit kontrol panelinden oluşur.

## Mevcut Durum

- Sensör üretimi ve MQTT yayın sözleşmesi unit testlerle doğrulanır.
- Subscriber veri doğrulaması ile PostgreSQL/SQL Server store sözleşmeleri fake DB
  bağlantısıyla test edilir.
- `DikeyTarimSQL` paketi normalize sensör kayıtları, view, procedure ve alarm trigger'ı içerir.
- XGBoost notebook mantığı `harvest_model.py` içinde tekrar kullanılabilir hale getirilmiştir.
- Panel, değiştirilebilir sensör ve tahmin sağlayıcıları kullanır.
- Streamlit giriş akışı AppTest ile doğrulanır.
- GitHub Actions CI; format, lint, unit/integration test ve coverage kapısını uygular.
- Staging workflow'u geçici MQTT broker, Streamlit, Playwright ve YOLO CPU smoke testi çalıştırır.
- Gerçek SQL Server çalıştırma testi henüz zorunlu CI kapsamında değildir.

## Proje Yapısı

```text
.
├── iot-bulut-mimarisi/           Sensör simülatörü, MQTT subscriber ve DB adaptörü
├── DikeyTarimSQL/                 SQL Server şeması, procedure, view ve trigger'lar
├── XGBoost-Hasat-Tahmin-Modeli/  Notebook, veri seti ve test edilebilir model modülü
├── Görüntü İşleme/               PlantSeg/YOLO eğitim ve tahmin araçları
├── projeuyp/                     Streamlit MES paneli ve sağlayıcı arayüzleri
├── tests/                        Unit, mock entegrasyon ve staging E2E testleri
├── docs/                         Test stratejisi ve doğrulanmış kalite raporu
└── .github/workflows/            CI ve geçici staging doğrulaması
```

## Kurulum

CI ile aynı ana sürüm Python 3.11'dir.

```bash
git clone https://github.com/mberatkaya/Endustri-4.0-Uyumlu-Dikey-Tarim-Fabrikasi.git
cd Endustri-4.0-Uyumlu-Dikey-Tarim-Fabrikasi

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

pip install -r requirements-dev.txt
pip install -r iot-bulut-mimarisi/requirements.txt
pip install -r projeuyp/requirements.txt
pip install -r XGBoost-Hasat-Tahmin-Modeli/requirements.txt
```

SQL Server backend'i kullanılacaksa resmi Microsoft sürücüsünü ayrıca kurun:

```bash
pip install -r iot-bulut-mimarisi/requirements-sqlserver.txt
```

macOS üzerinde XGBoost için OpenMP gerekebilir:

```bash
brew install libomp
```

## Test ve Kalite Kontrolü

Zorunlu unit ve mock entegrasyon testleri:

```bash
pytest tests/unit tests/integration \
  --cov=simulator.sensor_core \
  --cov=subscriber.message_processor \
  --cov=subscriber.sensor_store \
  --cov=projeuyp.services \
  --cov=harvest_model \
  --cov-branch \
  --cov-report=term-missing \
  --cov-fail-under=70
```

Kod kalitesi:

```bash
black --check .
isort --check-only .
flake8 .
pre-commit run --all-files
```

Yerel dosyaları otomatik kontrol etmek için:

```bash
pre-commit install
```

## Bileşenleri Çalıştırma

Sensör simülatörü:

```bash
python iot-bulut-mimarisi/simulator/sensor_simulator.py
```

MQTT subscriber:

```bash
python iot-bulut-mimarisi/subscriber/mqtt_subscriber.py
```

Streamlit panel:

```bash
streamlit run projeuyp/app.py
```

Panel varsayılan olarak üretilmiş sensör verisi kullanır. DB/API hazır olana kadar
deterministik test modu şu şekilde açılır:

```bash
PANEL_DATA_MODE=fake \
PREDICTION_MODE=fake \
FAKE_PREDICTION_DAYS=12 \
streamlit run projeuyp/app.py
```

Bağlantı bilgileri kaynak koda yazılmamalıdır. Varsayılan backend PostgreSQL'dir:

```text
DB_ENGINE=postgres
MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
```

SQL Server kullanmak için:

```text
DB_ENGINE=sqlserver
SQLSERVER_CONNECTION_STRING
```

`SQLSERVER_CONNECTION_STRING` verilmezse aşağıdaki alanlardan bağlantı dizesi oluşturulur:

```text
SQLSERVER_HOST, SQLSERVER_PORT, SQLSERVER_DATABASE
SQLSERVER_USER, SQLSERVER_PASSWORD
SQLSERVER_ENCRYPT, SQLSERVER_TRUST_CERTIFICATE
```

SQL Server ilk kurulumu boş bir sunucuda `DikeyTarimSQL/01_Veritabani.sql` ile
`12_Trigger.sql` arasındaki dosyalar numara sırasıyla çalıştırılarak yapılır.
`13_RaporSorgulari.sql` ve `14_TumCiktilariGoster.sql` kurulum değil, rapor/inceleme
sorgularıdır. MQTT'deki `plant_code`, `MarulParti.KonumKodu` alanındaki aktif partiyle
eşleşmelidir.

Gerçek tahmin modeli panelde kullanılacaksa:

```text
PREDICTION_MODE=model
HARVEST_MODEL_PATH=/absolute/path/to/trained_model.pkl
```

Modelin `ph, ec, temp, water_temp, hum, co2, light` sütunlarını bu sırayla kabul
etmesi gerekir. Notebook modeli farklı bir feature sözleşmesi kullandığı için doğrudan
panel modeli olarak sunulmaz.

## GitHub Flow

- `main` her zaman çalışır durumda tutulur.
- Çalışmalar `feature/*`, `fix/*` veya `test/*` branch'lerinde yapılır.
- Değişiklikler pull request ile `main` branch'ine alınır.
- `Lint and Format`, `Unit and Integration Tests` ve `CI Success` kontrolleri geçmelidir.
- En az bir onay ve squash merge kullanılır.

Detaylar:

- [Test stratejisi](docs/TEST_STRATEGY.md)
- [Kalite raporu](docs/QUALITY_REPORT.md)
