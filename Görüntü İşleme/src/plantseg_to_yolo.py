import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml



# AYARLAR

ROOT = Path(__file__).resolve().parents[1]

PLANTSEG_ROOT = ROOT / "data" / "plantseg" / "plantseg"  # Orijinal PlantSeg klasoru (images + annotations)
OUTPUT_ROOT = ROOT / "data" / "plantseg_yolo"            # Uretilecek YOLO veri seti klasoru

MIN_AREA = 10.0   # Bu alandan kucuk konturlari ele
EPSILON = 0.002   # Poligon sadelestirme katsayisi (ne kadar buyukse o kadar az nokta olur)

SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def read_mask(path: Path) -> np.ndarray:
    """Maske PNG'sini gri tonlamali (tek kanal) olarak okur.

    Turkce/ozel karakterli yollarda sorun cikmamasi icin dosyayi once
    np.fromfile ile byte olarak okuyup cv2.imdecode ile coozuyoruz (cv2.imread
    bazi Windows yollarinda hata çıkarmıştı
    """
    data = np.fromfile(str(path), dtype=np.uint8)
    mask = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise ValueError(f"Mask okunamadi: {path}")
    return mask


def find_image(dataset_root: Path, split: str, stem: str) -> Path:
    """Maske dosyasiyla ayni isimli ama uzantisi farkli olabilen goruntuyu bulur."""
    image_dir = dataset_root / "images" / split
    for extension in IMAGE_EXTENSIONS:
        image_path = image_dir / f"{stem}{extension}"
        if image_path.exists():
            return image_path
    raise FileNotFoundError(f"Gorsel bulunamadi: {image_dir / stem}")


def contour_to_yolo_line(contour: np.ndarray, width: int, height: int) -> str | None:
    """Tek bir konturu (kapali egriyi) YOLO segmentation etiket satirina cevirir.


    1) cv2.approxPolyDP ile konturu daha az noktayla temsil ederiz
       bu YOLO etiketini kuculten ve egitimi hizlandiran bir adimdir.
    2) Nokta sayisi 3'ten azsa poligon olusmaz, atlariz.
    3) Her (x, y) pikselini goruntu boyutuna bolerek 0-1 araligina normalize ederiz
       (YOLO koordinatlari hep 0-1 arasidir). Bastaki "0" sinif id'sidir (problem_region).

    Sonuc satir formati: "0 x1 y1 x2 y2 x3 y3 ..."
    """
    simplified = cv2.approxPolyDP(contour, EPSILON * cv2.arcLength(contour, True), True)
    points = simplified.reshape(-1, 2)
    if len(points) < 3:
        return None

    values = ["0"]  # Tek sinif: problem_region -> id = 0.
    for x, y in points:
        values.append(f"{min(max(x / width, 0), 1):.6f}")   # x'i 0-1'e normalize et ve sinirla.
        values.append(f"{min(max(y / height, 0), 1):.6f}")  # y'yi 0-1'e normalize et ve sinirla.
    return " ".join(values)


def mask_to_yolo_lines(mask: np.ndarray) -> list[str]:
    """Bir maske goruntusunden tum YOLO etiket satirlarini cikarir

    1) Maskede 0'dan buyuk her piksel "problem bolgesi" sayilir -> binary (0/1) maske
    2) cv2.findContours ile bu bolgelerin dis sinirlarini (konturlarini) buluruz
    3) Cok kucuk konturlar (MIN_AREA altinda) gurultudur, atlanir
    4) Kalan her kontur bir poligon etiket satirina cevrilir
    """
    problem_mask = (mask > 0).astype(np.uint8)
    height, width = problem_mask.shape
    # RETR_EXTERNAL: sadece dis konturlar
    # CHAIN_APPROX_SIMPLE: gereksiz ara noktalari atar.
    contours, _ = cv2.findContours(problem_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    lines: list[str] = []
    for contour in contours:
        if cv2.contourArea(contour) < MIN_AREA:
            continue
        line = contour_to_yolo_line(contour, width, height)
        if line:
            lines.append(line)
    return lines


def copy_image(source: Path, output_root: Path, split: str) -> None:
    """Orijinal goruntuyu YOLO klasorundeki images/<split> altina kopyalar."""
    target = output_root / "images" / split / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_data_yaml(output_root: Path) -> Path:
    """YOLO'nun veri setini tanimasi icin gereken data.yaml dosyasini yazar."""
    yaml_path = output_root / "data.yaml"
    data = {
        "path": output_root.as_posix(),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "problem_region"},  # Tek sinif.
    }
    yaml_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )
    return yaml_path


def convert_plantseg_to_yolo() -> None:
    """PlantSeg maskelerini bastan sona YOLO segmentation veri setine cevirir.

    Her split icin: maskeyi oku -> goruntuyu kopyala -> maskeyi YOLO etiketlerine
    cevir -> labels/<split>/<isim>.txt olarak yaz. Sonunda data.yaml uretilir.
    """
    # Cikti klasoru varsa silip sifirdan uretiyoruz (tekrar calistirilabilirlik icin)
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)

    print("PlantSeg -> YOLO donusumu basladi.")
    print(f"Kaynak PlantSeg klasoru: {PLANTSEG_ROOT}")
    print(f"Yeni YOLO klasoru: {OUTPUT_ROOT}")

    for split in SPLITS:
        annotation_dir = PLANTSEG_ROOT / "annotations" / split
        label_dir = OUTPUT_ROOT / "labels" / split
        label_dir.mkdir(parents=True, exist_ok=True)

        masks = sorted(annotation_dir.glob("*.png"))
        empty_count = 0  # Hic problem bolgesi cikmayan yani bos etiketli goruntu sayisi

        for mask_path in masks:
            image_path = find_image(PLANTSEG_ROOT, split, mask_path.stem)
            copy_image(image_path, OUTPUT_ROOT, split)

            mask = read_mask(mask_path)
            lines = mask_to_yolo_lines(mask)

            # Etiket dosyasini yaz (bos olsa bile, negatif ornek olarak bos dosya birakilir)
            label_path = label_dir / f"{mask_path.stem}.txt"
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            empty_count += int(not lines)

        print(f"{split}: {len(masks)} label uretildi, {empty_count} bos label")

    yaml_path = write_data_yaml(OUTPUT_ROOT)
    print(f"YOLO data yaml hazir: {yaml_path}")


def main() -> None:
    if not PLANTSEG_ROOT.exists():
        raise FileNotFoundError(
            f"PlantSeg klasoru yok: {PLANTSEG_ROOT}\n"
            "Once veri setini indir: .venv\\Scripts\\python.exe src\\download_dataset.py"
        )
    convert_plantseg_to_yolo()


if __name__ == "__main__":
    main()
