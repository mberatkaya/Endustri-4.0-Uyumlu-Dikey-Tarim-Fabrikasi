# XGBoost Hasat Tahmin Modeli

Bu klasor, dikey tarim verileriyle marul buyume/hasat gunu tahmini icin hazirlanan XGBoost tabanli Jupyter notebook calismasini icerir.

## Icerik

- `XGBoost-Hasat-Tahmin-Modeli.ipynb`: Model gelistirme ve tahmin notebook'u.
- `harvest_model.py`: Feature engineering, egitim, metrik ve tahmin fonksiyonlari.
- `data/lettuce_dataset.csv`: Egitim ve analiz verisi.
- `data/unseen_data.csv`: Modelin tahmin yapmasi icin kullanilan yeni veri.
- `requirements.txt`: Notebook'u calistirmak icin gereken Python paketleri.

## Calistirma

```bash
pip install -r requirements.txt
pip install jupyter
jupyter notebook XGBoost-Hasat-Tahmin-Modeli.ipynb
```

Notebook icindeki veri yollari `data/` klasorunu kullanir. Bu nedenle notebook'u bu klasor icinden calistirmak yeterlidir.
