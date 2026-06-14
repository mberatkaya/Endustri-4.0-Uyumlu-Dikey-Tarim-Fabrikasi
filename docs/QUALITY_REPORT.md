# Proje Kalite Raporu

## Doğrulama Özeti

Son yerel doğrulama tarihi: **14 Haziran 2026**

| Kontrol | Sonuç |
| --- | --- |
| Unit + mock entegrasyon testleri | 51/51 geçti |
| Çekirdek branch coverage | yüzde 92,19 |
| Black | sıfır hata |
| isort | sıfır hata |
| flake8 | sıfır hata |
| actionlint | sıfır hata |
| Staging E2E/smoke | 3/3 geçti |
| Kırık dahili Markdown bağlantısı | sıfır |
| `main` branch koruması | PR + 1 onay + `CI Success` zorunlu |

Coverage bileşenleri:

| Modül | Coverage |
| --- | ---: |
| `simulator.sensor_core` | yüzde 100,00 |
| `subscriber.message_processor` | yüzde 95,74 |
| `projeuyp.services` | yüzde 90,91 |
| `harvest_model` | yüzde 85,29 |

Bu değerler hem macOS arm64/Python 3.12 temiz sanal ortamında hem de Linux
arm64/Python 3.11 temiz Docker ortamında aynı sonuçla ölçülmüştür. GitHub Actions
sonuçları workflow remote'a alındıktan sonra esas sürekli kanıt olacaktır. GitHub
repository ayarlarında squash merge tek merge yöntemi olarak etkinleştirilmiş ve
merge sonrası branch silme açılmıştır.

## İlk Hata Raporu

### Düzeltilenler

| ID | Seviye | Bulgu | Çözüm |
| --- | --- | --- | --- |
| BUG-001 | Major | `ask_int` aralık karşılaştırması hatalıydı | Alt/üst sınır kontrolü düzeltildi ve test eklendi |
| BUG-002 | Major | Negatif büyüme günü son evreyi döndürüyordu | Gün değerleri ilk/son evreye clamp edildi |
| BUG-003 | Major | Testler gerçek evre kodlarıyla uyuşmuyordu | Beklentiler gerçek `E2-E7` sözleşmesine bağlandı |
| BUG-004 | Major | Entegrasyon fixture'ı sınıf kapsamı nedeniyle bulunamıyordu | Ortak fixture yapısı oluşturuldu |
| BUG-005 | Major | Coverage kapısı CI'da hatayı gizliyordu | `continue-on-error` ve hata yutan komutlar kaldırıldı |
| BUG-006 | Major | CD workflow'ları geçersiz reusable-workflow çağrısı yapıyordu | Sahte CD dosyaları kaldırılıp staging validation yazıldı |
| BUG-007 | Major | Panel model yolu çalışma dizinine bağlıydı | Yol panel modülüne göre veya env ile çözülüyor |
| BUG-008 | Minor | Black/isort/flake8 mevcut kaynakta başarısızdı | Kaynaklar formatlandı ve lint hataları giderildi |

### Açık Engeller ve Riskler

| ID | Seviye | Durum | Öncelikli aksiyon |
| --- | --- | --- | --- |
| BLOCK-001 | Major | Gerçek DB şeması ve migration dosyaları teslim edilmedi | DB ekibi tesliminden sonra fake cursor testini gerçek test DB testiyle genişlet |
| BLOCK-002 | Major | Sensör verisini panel için sunan gerçek API yok | API yanıt şemasını `SensorDataProvider` arayüzüne bağla |
| BLOCK-003 | Major | Notebook modeli panelin yedi sütunlu tahmin sözleşmesiyle uyumlu değil | Panel için ayrı model pipeline/artifact üret veya feature adapter yaz |
| RISK-001 | Major | Demo giriş bilgileri uygulama kodunda sabit | Gerçek dağıtımdan önce kimlik doğrulama servisi ve secret yönetimi ekle |
| RISK-002 | Minor | Staging kalıcı deployment değil | Hedef platform seçildiğinde environment ve deploy adımı ekle |

## E2E Durumu

Tam hedef akış:

```text
Sensör → MQTT → DB → API → Tahmin → Panel
```

Şu anda otomatik doğrulanan akış:

```text
Sensör çekirdeği → MQTT payload → Subscriber → Fake DB
Fake sensör sağlayıcısı → Deterministik tahmin → Streamlit panel
Geçici MQTT broker → Publish/Subscribe round-trip
best.pt → CPU inference smoke
```

DB ve API olmadan tam hedef akışın geçtiği iddia edilmez. `BLOCK-001` ve
`BLOCK-002` kapatıldıktan sonra aynı staging workflow gerçek test servisleriyle
genişletilecektir.

## Performans Baseline

Başlangıç baseline'ı yalnızca aynı donanımda sonraki değişiklikleri karşılaştırmak için
kullanılır; henüz ürün SLA'sı değildir. Ölçümler Apple M4, 24 GiB RAM, macOS arm64
ve Python 3.12 üzerinde yapılmıştır. Medyan değerler yedi tekrar üzerinden alınmıştır.

| Metrik | Son ölçüm | Durum |
| --- | ---: | --- |
| Sensör `Plant.measure()` medyan süresi | 0,0055 ms | 5.000 çağrı/tekrar |
| Deterministik panel tahmini medyan süresi | <0,001 ms | 100.000 çağrı/tekrar |
| XGBoost tek satır tahmin medyan süresi | 0,627 ms | 1.000 çağrı/tekrar, 30 feature |
| Streamlit health endpoint | medyan 0,413 ms; p95 0,500 ms | 15 yerel istek |

Donanım, veri boyutu ve tekrar sayısı belirtilmeden performans sonucu yayımlanmaz.

## MÜDEK Kanıt Eşleştirmesi

MÜDEK bir yazılım reposunu tek başına akredite etmez; mühendislik eğitim programını
değerlendirir. Bu tablo yalnızca projenin program çıktıları için üretebildiği teknik
kanıtları gösterir ve uyumluluk yüzdesi vermez.

Referans: [MÜDEK Mühendislik Lisans Programları Değerlendirme Ölçütleri,
Sürüm 3.1](https://www.mudek.org.tr/tr/belge/doc.shtm)

| İlgili program çıktısı | Repo kanıtı | Kanıt durumu |
| --- | --- | --- |
| Problem analizi | Hata raporu, önceliklendirme ve düzeltilen test hataları | Mevcut |
| Mühendislik tasarımı | Sensör, subscriber, model ve panel sağlayıcı sözleşmeleri | Mevcut |
| Teknik ve araçların kullanımı | pytest, coverage, GitHub Actions, MQTT, XGBoost, YOLO | Mevcut |
| Araştırma ve inceleme | PlantSeg değerlendirmeleri ve model metrik görselleri | Bileşen README'sinde mevcut |
| Bireysel ve takım çalışması | GitHub Flow, PR şablonu ve inceleme kuralı | Süreç tanımlı; PR geçmişiyle kanıtlanmalı |
| Sözlü ve yazılı iletişim | README, test stratejisi ve kalite raporu | Mevcut |
| Proje yönetimi | Branch stratejisi, kalite kapıları, hata öncelikleri | Mevcut |
| Yaşam boyu öğrenme | Sürekli ölçüm ve iyileştirme yaklaşımı | Süreç tanımlı |

Program düzeyindeki kazanım ölçümü, öğrenci değerlendirmesi ve eğitim planı kanıtları
repo kapsamı dışındadır; bölümün MÜDEK özdeğerlendirme sürecinde ayrıca ele alınmalıdır.
