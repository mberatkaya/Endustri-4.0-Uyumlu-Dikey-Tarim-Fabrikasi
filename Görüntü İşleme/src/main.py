from pathlib import Path

from ultralytics import YOLO



# AYARLAR



# ROOT = "Görüntü İşleme" klasoru __file__ = src/main.py parents[1] = src'nin ust klasoru
ROOT = Path(__file__).resolve().parents[1]

# Egitimde kullanilacak YOLO veri seti augmentasyon adimi bunu uretir
DATA_YAML = ROOT / "data" / "plantseg_yolo_augmented" / "data.yaml"

MODEL = "yolo26n-seg.pt"  # Baslangic agirligi YOLO26 nano segmentation modeli uzerine egitilecegi icin
EPOCHS = 300              # Toplam egitim turu sayisi
PATIENCE = 30            # 30 tur boyunca iyilesme yoksa erken durdur (early stopping)
IMGSZ = 640              # Egitim gorsel boyutu (640x640)
BATCH = -1               # -1 => Ultralytics VRAM'e gore batch'i otomatik secer
DEVICE = "0"             # GPU icin "0", CPU icin "cpu"
WORKERS = 4              # Veriyi okuyan paralel islem (worker) sayisi
CACHE = False            # Goruntuleri RAM/disk'te onbellege alma 16 GB RAM icin kapali
DETERMINISTIC = False    # Tam tekrarlanabilirlik (biraz yavaslatir)

# Egitim ciktilarinin (grafikler, agirliklar, sonuclar) yazilacagi klasor.
TRAIN_OUTPUT = ROOT / "outputs" / "training"


def train() -> None:
    """YOLO segmentation modelini PlantSeg verisi uzerinde egitir.

    Ultralytics YOLO modelini yukler ve `model.train()` cagrisina
    yukaridaki ayarlari verir. Egitim bittiginde en iyi agirlik
    `outputs/training/plantseg_problem_region/weights/best.pt` icine yazilir.
    """
    print("YOLO egitimi basliyor.")
    print(f"Data yaml: {DATA_YAML}")
    print(f"Model: {MODEL}")
    print(
        f"Epochs: {EPOCHS}, patience: {PATIENCE}, imgsz: {IMGSZ}, "
        f"batch: {BATCH}, device: {DEVICE}, workers: {WORKERS}, cache: {CACHE}"
    )

    model = YOLO(MODEL)
    model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        patience=PATIENCE,
        imgsz=IMGSZ,
        batch=BATCH,
        device=DEVICE,
        workers=WORKERS,
        cache=CACHE,
        project=str(TRAIN_OUTPUT),
        name="plantseg_problem_region",
        exist_ok=True,
        plots=True,            # Egitim grafiklerini otomatik uretir.
        deterministic=DETERMINISTIC,
    )


def main() -> None:
    # Egitime baslamadan once veri setinin hazir olup olmadigini kontrol ediyoruz.
    if not DATA_YAML.exists():
        raise FileNotFoundError(
            f"YOLO data yaml bulunamadi: {DATA_YAML}\n"
            "Once PlantSeg -> YOLO donusumunu, sonra augmentation adimini calistir:\n"
            ".venv\\Scripts\\python.exe src\\plantseg_to_yolo.py\n"
            ".venv\\Scripts\\python.exe src\\augment_yolo.py"
        )
    train()


if __name__ == "__main__":
    main()
