from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

# AYARLAR
# SOURCE'u degistirerek resim, video ya da webcam ile tahmin yapilabilir.

ROOT = Path(__file__).resolve().parents[1]

SOURCE = "0"  # "0" = webcam. Resim/video icin yol yaz: "test.jpg" veya "video.mp4"
WEIGHTS = ROOT / "models" / "best.pt"  # Egitilmis modelin agirliklari
CONF = 0.25  # Guven esigi: bunun altindaki tahminler gosterilmez
IMGSZ = 640  # Tahmin gorsel boyutu
OUTPUT = None  # Sonucu kaydetmek icin yol (orn. "outputs/tahmin.mp4"); None = sadece ekranda goster
MAX_FRAMES = None  # Video icin en fazla kac kare islensin (None = hepsi)

WINDOW_NAME = "PlantSeg problem_region tahmini"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_image(path: Path) -> np.ndarray:
    """Turkce/ozel karakterli yollar icin guvenli resim okuma."""
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Resim okunamadi: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    """Turkce/ozel karakterli yollar icin guvenli resim yazma."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix, image)
    if not ok:
        raise ValueError(f"Resim yazilamadi: {path}")
    encoded.tofile(str(path))


def parse_source(value: str) -> int | Path:
    """Webcam icin rakam (orn. "0") -> int; aksi halde dosya yolu -> Path dondurur."""
    if value.isdigit():
        return int(value)
    return Path(value)


def predict_frame(
    model: Any, frame: np.ndarray, conf: float = CONF, imgsz: int = IMGSZ
) -> np.ndarray:
    """Tek bir kare/goruntu uzerinde tahmin yapar ve cizilmis goruntuyu dondurur.

    model.predict tahmin sonuclarini verir, .plot() bu sonuclari (maske + kutu)
    orijinal goruntunun uzerine cizip yeni bir goruntu olarak dondurur.
    """
    results = model.predict(frame, conf=conf, imgsz=imgsz, verbose=False)
    return results[0].plot()


def show_image(model: Any, image_path: Path) -> None:
    """Tek bir resim icin tahmini ekranda gosterir veya dosyaya kaydeder."""
    prediction = predict_frame(model, read_image(image_path))

    if OUTPUT is not None:
        write_image(Path(OUTPUT), prediction)
        print(f"Tahmin gorseli yazildi: {OUTPUT}")
        return

    cv2.imshow(WINDOW_NAME, prediction)
    cv2.waitKey(0)  # Tusa basilana kadar bekle.
    cv2.destroyAllWindows()


def show_video_or_webcam(model: Any, source: str | int) -> None:
    """Video dosyasi veya webcam icin kare kare tahmin yapar.

    Her kareyi okur, tahmin eder ve ya ekranda gosterir ya da (OUTPUT verilmisse)
    bir video dosyasina yazar. Ekranda gosterirken 'q' veya ESC ile cikilir.
    """
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise FileNotFoundError(f"Video/webcam acilamadi: {source}")

    # OUTPUT verilmisse, tahmin karelerini bir mp4 dosyasina yazmak icin yazici hazirla.
    writer = None
    if OUTPUT is not None:
        out_path = Path(OUTPUT)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    frame_count = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break  # Video bitti veya kare okunamadi.

        prediction = predict_frame(model, frame)
        if writer is not None:
            writer.write(prediction)
        else:
            cv2.imshow(WINDOW_NAME, prediction)
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):  # ESC veya 'q' ile cik.
                break

        frame_count += 1
        if MAX_FRAMES is not None and frame_count >= MAX_FRAMES:
            break

    capture.release()
    if writer is not None:
        writer.release()
        print(f"Tahmin videosu yazildi: {OUTPUT}")
    else:
        cv2.destroyAllWindows()


def main() -> None:
    from ultralytics import YOLO

    weights = WEIGHTS.resolve()
    if not weights.exists():
        raise FileNotFoundError(f"Model bulunamadi: {weights}")

    model = YOLO(str(weights))
    source = parse_source(SOURCE)

    # SOURCE sadece rakamsa (orn. "0") webcam'dir; degilse dosya yoludur.
    if isinstance(source, int):
        show_video_or_webcam(model, source)
        return

    source_path = source.resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Kaynak bulunamadi: {source_path}")

    # Uzantiya bakarak resim mi video mu oldugunu anla.
    if source_path.suffix.lower() in IMAGE_EXTENSIONS:
        show_image(model, source_path)
    else:
        show_video_or_webcam(model, str(source_path))


if __name__ == "__main__":
    main()
