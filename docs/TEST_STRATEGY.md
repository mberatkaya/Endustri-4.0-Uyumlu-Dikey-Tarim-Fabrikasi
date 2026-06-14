# Test Stratejisi ve CI/CD Tasarımı

## Amaç

Bu strateji sensör verisinin üretilmesinden panelde gösterilmesine kadar yazılım
bileşenlerinin doğrulanmasını ve hatalı kodun `main` branch'ine alınmamasını amaçlar.
SQL Server şeması repoda bulunur; ancak CI'da gerçek veritabanı servisi açılmadığından
store ve şema testleri fake adaptörlerle çalışır ve canlı entegrasyon kanıtı sayılmaz.

## Test Türleri

### Unit Test

Tek bir fonksiyon veya sınıfın dış servislere bağlanmadan doğrulanmasıdır.

- Sensör evresi, fiziksel değer sınırları, alarm ve MQTT topic üretimi
- Subscriber payload doğrulaması, PostgreSQL ve SQL Server store parametreleri
- `DikeyTarimSQL` dosya sırası, normalize şema, altı evre, procedure ve trigger sözleşmesi
- Panel sensör/tahmin sağlayıcıları
- XGBoost feature engineering, eğitim ve metrik hesaplama
- YOLO tahmin fonksiyonunun model mock'u ile çağrılması
- Streamlit giriş ekranının AppTest ile doğrulanması

### Mock Entegrasyon Testi

Birden fazla gerçek proje modülünün kontrollü fake bağımlılıkla birlikte çalışmasıdır.

- `Plant.measure → publish → process_message → PostgreSQL/SQL Server store → fake DB cursor`
- `FakeSensorDataProvider → DeterministicPredictionProvider`

Bu testlerde MQTT publish fonksiyonu, subscriber, transaction yönetimi ve SQL üretimi
gerçek koddur. Veritabanı bağlantısı fake olduğu için sonuç "gerçek DB entegrasyonu
geçti" şeklinde raporlanmaz.

### E2E ve Staging Testi

`.github/workflows/staging.yml` geçici doğrulama ortamı kurar:

1. Anonymous erişimli geçici Mosquitto broker başlatılır.
2. Panel fake sensör ve deterministik tahmin modunda çalıştırılır.
3. Streamlit health endpoint kontrol edilir.
4. Playwright ile operatör girişi, üretim başlatma, sensör ve tahmin gösterimi doğrulanır.
5. MQTT publish/subscribe round-trip testi çalıştırılır.
6. Repodaki `Görüntü İşleme/models/best.pt` modeli CPU üzerinde tek görüntüyle çalıştırılır.

Bu workflow kalıcı bir bulut staging deployment değildir.

## Bileşen Kabul Kriterleri

| Bileşen | Kabul kriteri | Otomatik kanıt |
| --- | --- | --- |
| Sensör çekirdeği | Gün sınırları doğru evreye eşlenir; altı sensör üretilir; değerler fiziksel sınırdadır | `tests/unit/test_iot_simulator.py` |
| MQTT yayın | Normal veri QoS 1 ile doğru topic'e, alarm QoS 2 ile alarm topic'ine gider | Unit ve entegrasyon testleri |
| Subscriber | Eksik/geçersiz payload reddedilir; doğrulanmış veri seçili store'a iletilir | `test_mqtt_subscriber.py` |
| DB adaptörleri | PostgreSQL tek transaction kullanır; SQL Server procedure çağırır; hatalar rollback edilir | `test_sensor_store.py` |
| SQL Server şeması | Dosya sırası, normalize sensör modeli, altı evre, view/procedure/trigger sözleşmesi korunur | `test_dikey_tarim_sql.py` |
| Sensör → DB | Aynı MQTT payload'ı iki backend'in fake bağlantısına doğru parametrelerle ulaşır | `test_sensor_to_db_flow.py` |
| XGBoost | Lag/rolling feature'lar bitki bazında hesaplanır; gerçek XGBoost modeli eğitilip tahmin yapar | `test_xgboost_model.py` |
| Panel servisleri | Negatif/aşırı günler clamp edilir; fake veri deterministiktir; model sütun sırası sabittir | `test_dashboard_services.py` |
| Streamlit panel | Giriş ekranı çalışır; staging'de üretim başlatılır ve tahmin görünür | AppTest ve Playwright |
| YOLO | Mock model çağrı sözleşmesi geçer; staging'de `best.pt` CPU inference üretir | Unit test ve staging smoke |

Gerçek DB ortamı/API hazır olduğunda ek kabul kriterleri:

- Test verisi gerçek test şemasına yazılmalı ve aynı kimlikle geri okunmalıdır.
- API yanıt şeması panel sağlayıcısının yedi sensör alanını sağlamalıdır.
- Sensör timestamp'i ile API/panel görünümü arasındaki p95 gecikme ölçülmelidir.
- Test sonunda oluşturulan kayıtlar izole test şemasından temizlenmelidir.

## Kalite Kapıları

Pull request için zorunlu kriterler:

- Black format kontrolü: sıfır hata
- isort import kontrolü: sıfır hata
- flake8: sıfır hata
- Unit ve mock entegrasyon testleri: yüzde 100 başarılı
- Çekirdek iş kuralları coverage: en az yüzde 70, hedef yüzde 75 ve üzeri
- GitHub Actions YAML kontrolü: actionlint sıfır hata
- En az bir pull request onayı

Coverage kapsamı framework/CLI gövdeleri yerine şu iş kuralı modülleridir:

```text
simulator.sensor_core
subscriber.message_processor
subscriber.sensor_store
projeuyp.services
harvest_model
```

Streamlit UI ve komut satırı giriş noktaları AppTest/E2E ile ayrıca doğrulanır.

## Branch Stratejisi

GitHub Flow kullanılır:

1. Güncel `main` üzerinden `feature/*`, `fix/*` veya `test/*` branch'i açılır.
2. Değişiklik ve testler aynı pull request içinde tutulur.
3. CI kontrolleri ve en az bir inceleme onayı beklenir.
4. Squash merge ile `main` güncellenir.
5. `main` güncellemesinden sonra staging validation çalışır.

Uzun ömürlü `develop`, `release/*` ve `hotfix/*` branch'leri kullanılmaz.

## Hata Öncelikleri

| Seviye | Tanım | Hedef tepki |
| --- | --- | --- |
| Critical / P0 | Veri kaybı, güvenlik ihlali, sistemin tamamen çalışmaması | Aynı gün |
| Major / P1 | Ana kullanıcı akışının veya bileşen entegrasyonunun çalışmaması | İlk uygun düzeltme |
| Minor / P2 | Ana akışı engellemeyen hata veya eksik doğrulama | Planlı iterasyon |

Hata kaydı için `.github/ISSUE_TEMPLATE/bug_report.md` kullanılır.

## Raporlama

CI aşağıdaki artifact'leri üretir:

- JUnit test raporu
- Coverage XML
- Coverage HTML
- Staging Streamlit logu
- Playwright/staging JUnit raporu
- YOLO smoke JUnit raporu

Ölçülmeyen performans veya kalite değerleri başarı sonucu olarak yazılmaz.
