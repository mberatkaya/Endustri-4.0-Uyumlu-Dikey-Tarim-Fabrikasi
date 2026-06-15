import random
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml



# AYARLAR


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "data" / "plantseg_yolo"             # plantseg_to_yolo.py ciktisi
OUTPUT_ROOT = ROOT / "data" / "plantseg_yolo_augmented"  # Augmente edilmis veri seti

IMAGE_SIZE = 640   # Tum ciktilar bu boyuta getirilmesi gerekli cunku input olarak yolo'ya 640
RANDOM_SEED = 42   # Sabit seed'den dolayı her calistirmada aynı augmentasyonlar uretilir, deterministlik için önemli
VARIATIONS_PER_TRAIN_IMAGE = 3  # Her train goruntusu icin base disinda kac varyasyon uretilecek bunu belirliyoruz

HUE_SHIFT = 8           # Renk tonu kaydiriliyor
SATURATION_SCALE = 1.15  # Doygunluk carpani
CROP_SIZE = 560         # Crop alinacak kare boyutu Problemli bölümü kaybetmemek önemli
CROP_PADDING = 20       # Crop kenar payi

SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


# ---------------------------------------------------------------------------
# Dosya okuma/yazma yardimcilari
# ---------------------------------------------------------------------------
def read_image(path: Path) -> np.ndarray:
    # Turkce veya ozel karakterli yollar icin np.fromfile + cv2.imdecode kullaniyoruz.
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Gorsel okunamadi: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix, image)
    if not ok:
        raise ValueError(f"Gorsel yazilamadi: {path}")
    encoded.tofile(str(path))


def read_labels(path: Path) -> list[tuple[int, np.ndarray]]:
    """YOLO etiket dosyasini (class_id, poligon noktalari) listesine cevirir.

    Her satir: "class_id x1 y1 x2 y2 ...". Noktalar 0-1 normalize,
    seklinde numpy dizisine konur.
    """
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []

    labels: list[tuple[int, np.ndarray]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        class_id = int(parts[0])
        points = np.array([float(value) for value in parts[1:]], dtype=np.float32).reshape(-1, 2)
        labels.append((class_id, points))
    return labels


def write_labels(path: Path, labels: list[tuple[int, np.ndarray]]) -> None:
    """Etiketleri tekrar YOLO formatinda yazar ve 3 noktadan az poligonlari atar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for class_id, points in labels:
        if len(points) < 3:
            continue
        values = [str(class_id)]
        for x, y in points:
            values.append(f"{float(np.clip(x, 0, 1)):.6f}")  # Koordinatlari 0-1'e sabitle.
            values.append(f"{float(np.clip(y, 0, 1)):.6f}")
        lines.append(" ".join(values))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")



# Poligon temizleme yardimcilari

def polygon_area(points: np.ndarray) -> float:
    """Poligon alanini hesaplar

    Augmentasyon sonrasi cok kuculen/bozulan poligonlari elemek icin kullanilir.
    """
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def remove_repeated_points(points: np.ndarray) -> np.ndarray:
    """Art arda tekrar eden ayni noktalari ve baş==son olan noktayi temizler."""
    if len(points) == 0:
        return points

    rounded = np.round(points, 6)
    keep = [0]
    for index in range(1, len(rounded)):
        if not np.array_equal(rounded[index], rounded[keep[-1]]):
            keep.append(index)

    cleaned = points[keep]
    if len(cleaned) > 1 and np.array_equal(np.round(cleaned[0], 6), np.round(cleaned[-1], 6)):
        cleaned = cleaned[:-1]
    return cleaned


def clean_labels(labels: list[tuple[int, np.ndarray]]) -> list[tuple[int, np.ndarray]]:
    """Donusumden sonra gecersiz hale gelen poligonlari atar.

    noktalar 0-1'e kirpilir, tekrar eden noktalar atilir, en az 3 nokta ve
    minik bir alandan buyuk olanlar saklanir
    """
    cleaned = []
    for class_id, points in labels:
        points = remove_repeated_points(np.clip(points, 0, 1))
        if len(points) >= 3 and polygon_area(points) > 0.00001:
            cleaned.append((class_id, points.astype(np.float32)))
    return cleaned



# Goruntu donusumleri (her biri AYNI ZAMANDA etiketleri de gunceller)

def resize_to_training_size(image: np.ndarray) -> np.ndarray:
    # Tum goruntuleri ayni egitim boyutuna getir.
    return cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)


def flip_labels(labels, horizontal: bool, vertical: bool):
    """Goruntu aynalaninca poligon noktalarini da aynalar.

    Yatay aynalamada x -> 1 - x, dikey aynalamada y -> 1 - y (koordinatlar 0-1) arasında olmak uzere
    """
    flipped = []
    for class_id, points in labels:
        new_points = points.copy()
        if horizontal:
            new_points[:, 0] = 1.0 - new_points[:, 0]
        if vertical:
            new_points[:, 1] = 1.0 - new_points[:, 1]
        flipped.append((class_id, new_points))
    return clean_labels(flipped)


def rotate_image_and_labels(image: np.ndarray, labels, angle: float):
    """Goruntuyu ve poligonlari merkez etrafinda 'angle' degree dondurur.

    
    1) cv2.getRotationMatrix2D ile 2x3 Affine donusum matrisi uretilir.
    2) Goruntu warpAffine ile dondurulur bos kalan kenarlar BORDER_REFLECT_101
       (yansitma) ile doldurulur, siyah bant bu sayede olusmaz
    3) Poligon noktalari once piksele cevrilir, ayni matrisle carpilarak dondurulur,
       sonra tekrar 0-1'e normalize edilir. Boylece maske goruntuyle hizali kalir
    """
    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    rotated_image = cv2.warpAffine(
        image, matrix, (width, height),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101,
    )

    rotated_labels = []
    for class_id, points in labels:
        pixel_points = points * np.array([width, height], dtype=np.float32)
        ones = np.ones((len(pixel_points), 1), dtype=np.float32)
        transformed = np.hstack([pixel_points, ones]) @ matrix.T  # [x y 1] . matris = dondurulmus nokta.
        transformed[:, 0] /= width
        transformed[:, 1] /= height
        rotated_labels.append((class_id, transformed.astype(np.float32)))

    return rotated_image, clean_labels(rotated_labels)


def change_brightness_contrast(image: np.ndarray, brightness: int = 0, contrast: float = 1.0) -> np.ndarray:
    """Parlaklik ve kontrasti degistirir, Poligonlar degismez sadece piksel degerleri."""
    adjusted = image.astype(np.float32) * contrast + brightness
    return np.clip(adjusted, 0, 255).astype(np.uint8)  # Degerleri gecerli 0-255 araliginda tut.


def color_jitter(image: np.ndarray) -> np.ndarray:
    """Renk tonu ve doygunlugu degistirir 

    BGR'den HSV uzayina gecip H (ton) ve S (doygunluk) kanallarini oynar, sonra
    geri BGR'ye cevirir. Hue 0-180 dongusel oldugu icin % 180 alinir.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + HUE_SHIFT) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * SATURATION_SCALE, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def mask_protected_crop(image: np.ndarray, labels, rng: random.Random):
    """Problemli bolgeyi kaybetmeden rastgele bir kare crop alir.

    1) Etiket varsa tum poligon noktalarini (bounding box) bulunur
    2) Crop boyutu, bu kutuyu payiyla birlikte tamamen icine alacak kadar buyutulur
    3) Crop'un sol-ust kosesi, kutuyu disarida birakmayacak araliktan rastgele
       secilir (rng için seed burada kullanilir). Etiket yoksa merkezden crop alinir
    4) Crop tekrar IMAGE_SIZE'a olceklenir ve poligonlar yeni kareye gore normalize edilir
    """
    height, width = image.shape[:2]
    crop_size = min(CROP_SIZE, width, height)

    if labels:
        all_points = np.vstack([points for _, points in labels])
        pixel_points = all_points * np.array([width, height], dtype=np.float32)
        x1, y1 = np.floor(pixel_points.min(axis=0)).astype(int)
        x2, y2 = np.ceil(pixel_points.max(axis=0)).astype(int)

        # Crop, problemli bolgenin tamamini icine alacak kadar buyutulur.
        needed_size = max(x2 - x1, y2 - y1) + (2 * CROP_PADDING)
        crop_size = int(min(max(crop_size, needed_size), width, height))

        min_left = max(0, x2 - crop_size)
        max_left = min(x1, width - crop_size)
        min_top = max(0, y2 - crop_size)
        max_top = min(y1, height - crop_size)
    else:
        # Etiket yoksa merkez crop yeterli.
        min_left = max_left = (width - crop_size) // 2
        min_top = max_top = (height - crop_size) // 2

    left = rng.randint(int(min_left), int(max_left)) if max_left >= min_left else int(min_left)
    top = rng.randint(int(min_top), int(max_top)) if max_top >= min_top else int(min_top)

    cropped = image[top : top + crop_size, left : left + crop_size]
    cropped = cv2.resize(cropped, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)

    cropped_labels = []
    for class_id, points in labels:
        pixel_points = points * np.array([width, height], dtype=np.float32)
        pixel_points[:, 0] = (pixel_points[:, 0] - left) / crop_size
        pixel_points[:, 1] = (pixel_points[:, 1] - top) / crop_size
        cropped_labels.append((class_id, pixel_points.astype(np.float32)))

    return cropped, clean_labels(cropped_labels)



# Augmentasyon listesi
# Her oge: (dosya_eki, fonksiyon). Fonksiyon (goruntu, etiketler, rng) alir ve
# (yeni_goruntu, yeni_etiketler) dondurur. rng sadece crop'ta kullanilir.
# rng.sample bu listeden secim yapar.

VARIATIONS = [
    ("rot_-10",        lambda img, lbl, rng: rotate_image_and_labels(img, lbl, -10)),
    ("rot_+10",        lambda img, lbl, rng: rotate_image_and_labels(img, lbl, 10)),
    ("hflip",          lambda img, lbl, rng: (cv2.flip(img, 1), flip_labels(lbl, horizontal=True, vertical=False))),
    ("vflip",          lambda img, lbl, rng: (cv2.flip(img, 0), flip_labels(lbl, horizontal=False, vertical=True))),
    ("brightness_-25", lambda img, lbl, rng: (change_brightness_contrast(img, brightness=-25), lbl)),
    ("brightness_+25", lambda img, lbl, rng: (change_brightness_contrast(img, brightness=25), lbl)),
    ("contrast_0.85",  lambda img, lbl, rng: (change_brightness_contrast(img, contrast=0.85), lbl)),
    ("contrast_1.15",  lambda img, lbl, rng: (change_brightness_contrast(img, contrast=1.15), lbl)),
    ("color_jitter",   lambda img, lbl, rng: (color_jitter(img), lbl)),
    ("mask_crop",      lambda img, lbl, rng: mask_protected_crop(img, lbl, rng)),
]


def save_sample(output_root: Path, split: str, image_path: Path, suffix: str, image: np.ndarray, labels) -> None:
    """Bir goruntu + etiket ciftini cikti veri setine '<isim>_<ek>' adiyla yazar."""
    output_image = output_root / "images" / split / f"{image_path.stem}_{suffix}{image_path.suffix}"
    output_label = output_root / "labels" / split / f"{image_path.stem}_{suffix}.txt"
    write_image(output_image, image)
    write_labels(output_label, labels)


def write_data_yaml(output_root: Path) -> None:
    data = {
        "path": output_root.as_posix(),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "problem_region"},
    }
    (output_root / "data.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )


def augment_dataset() -> None:
    """Tum veri setini gezer. val/test'i sadece olcekler, train'i ayrica augmente eder.

    Sabit RANDOM_SEED sayesinde her calistirmada ayni varyasyonlar secilir.
    """
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)  # Tekrar calistirilabilir olsun diye sifirdan uret

    rng = random.Random(RANDOM_SEED)
    print(
        f"Varyasyon ayari: train icin base + {VARIATIONS_PER_TRAIN_IMAGE}; "
        f"val/test icin sadece base. Tum ciktilar {IMAGE_SIZE}x{IMAGE_SIZE}."
    )

    for split in SPLITS:
        image_dir = INPUT_ROOT / "images" / split
        label_dir = INPUT_ROOT / "labels" / split
        image_paths = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)

        for image_path in image_paths:
            label_path = label_dir / f"{image_path.stem}.txt"
            image = resize_to_training_size(read_image(image_path))
            labels = read_labels(label_path)

            # Orijinal (sadece olceklenmis) ornek her zaman yazilir.
            save_sample(OUTPUT_ROOT, split, image_path, "base", image, labels)

            # Augmentasyon SADECE train icin; val/test bozulmadan kalmali.
            if split != "train":
                continue

            # Bu goruntu icin rastgele VARIATIONS_PER_TRAIN_IMAGE adet varyasyon sec ve uygula.
            for suffix, apply_variation in rng.sample(VARIATIONS, VARIATIONS_PER_TRAIN_IMAGE):
                augmented_image, augmented_labels = apply_variation(image, labels, rng)
                save_sample(OUTPUT_ROOT, split, image_path, suffix, augmented_image, augmented_labels)

        print(f"{split}: {len(image_paths)} kaynak gorsel islendi.")

    write_data_yaml(OUTPUT_ROOT)
    print(f"Augmented YOLO veri seti hazir: {OUTPUT_ROOT}")


def main() -> None:
    if not INPUT_ROOT.exists():
        raise FileNotFoundError(
            f"YOLO veri seti bulunamadi: {INPUT_ROOT}\n"
            "Once PlantSeg -> YOLO donusumu icin src\\plantseg_to_yolo.py dosyasini calistir."
        )
    augment_dataset()


if __name__ == "__main__":
    main()
