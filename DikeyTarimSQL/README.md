# DikeyTarimSQL

Bu klasor Microsoft SQL Server icin ilk kurulum betiklerini icerir.

## Kurulum

Bos bir SQL Server instance'inda `01_Veritabani.sql` ile `12_Trigger.sql`
arasindaki dosyalari numara sirasiyla calistirin.

- `01-09`: veritabani, tablolar ve ornek veriler
- `10`: view'lar
- `11`: sensor ve operator stored procedure'leri
- `12`: alarm kaydi olusturan trigger
- `13-14`: kurulum disi rapor ve inceleme sorgulari

MQTT payload'indaki `plant_code`, aktif `MarulParti.KonumKodu` degeriyle
eslesmelidir. `sp_SensorVerisiEkle`, eslesen aktif partiyi bulamazsa `50001`
numarali hatayi uretir.

Python subscriber'da bu backend'i kullanmak icin:

```bash
pip install -r iot-bulut-mimarisi/requirements-sqlserver.txt
export DB_ENGINE=sqlserver
export SQLSERVER_CONNECTION_STRING="Server=localhost,1433;Database=DikeyTarimDB;UID=sa;PWD=secret;Encrypt=yes;TrustServerCertificate=yes"
python iot-bulut-mimarisi/subscriber/mqtt_subscriber.py
```

Zorunlu CI testleri SQL dosyalarinin ve procedure parametrelerinin sozlesmesini
fake baglanti ile dogrular. Gercek SQL Server instance'i acmaz.
