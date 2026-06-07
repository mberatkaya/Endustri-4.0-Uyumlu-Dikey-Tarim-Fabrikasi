from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "data" / "plantseg_yolo"
OUTPUT_ROOT = ROOT / "data" / "plantseg_yolo_augmented"

# Hocaya anlatirken en onemli ayarlar burasi.
# Degerleri buradan kolayca degistirebilirsin.
IMAGE_SIZE = 640
RANDOM_SEED = 42

ROTATION_ANGLES = [-10, 10]  # Kamera acisi degisimi icin kontrollu dondurme.
USE_HORIZONTAL_FLIP = True
USE_VERTICAL_FLIP = True

BRIGHTNESS_VALUES = [-25, 25]  # LED/golge farki icin parlaklik degisimi.
CONTRAST_VALUES = [0.85, 1.15]  # Kontrast degisimi.

USE_COLOR_JITTER = True
HUE_SHIFT = 8  # Renk sicakligi/kamera sensor farki icin HSV hue kaydirma.
SATURATION_SCALE = 1.15

USE_MASK_PROTECTED_CROP = True
CROP_SIZE = 560  # Problemli bolgeyi kaybetmeden 640'tan alinacak kare crop.
CROP_PADDING = 20

# Her train gorseli icin base disinda kac augmentasyon uretilecegi.
# Komut satirindan --variations ile degistirilebilir.
VARIATIONS_PER_TRAIN_IMAGE = 3

SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_image(path: Path) -> np.ndarray:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for class_id, points in labels:
        if len(points) < 3:
            continue
        values = [str(class_id)]
        for x, y in points:
            values.append(f"{float(np.clip(x, 0, 1)):.6f}")
            values.append(f"{float(np.clip(y, 0, 1)):.6f}")
        lines.append(" ".join(values))

    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def polygon_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def remove_repeated_points(points: np.ndarray) -> np.ndarray:
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
    cleaned = []
    for class_id, points in labels:
        points = remove_repeated_points(np.clip(points, 0, 1))
        if len(points) >= 3 and polygon_area(points) > 0.00001:
            cleaned.append((class_id, points.astype(np.float32)))
    return cleaned


def resize_to_training_size(image: np.ndarray) -> np.ndarray:
    # YOLO egitiminde tum gorselleri ayni boyuta getiriyoruz.
    return cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)


def flip_labels(labels: list[tuple[int, np.ndarray]], horizontal: bool, vertical: bool) -> list[tuple[int, np.ndarray]]:
    flipped = []
    for class_id, points in labels:
        new_points = points.copy()
        if horizontal:
            new_points[:, 0] = 1.0 - new_points[:, 0]
        if vertical:
            new_points[:, 1] = 1.0 - new_points[:, 1]
        flipped.append((class_id, new_points))
    return clean_labels(flipped)


def rotate_image_and_labels(image: np.ndarray, labels: list[tuple[int, np.ndarray]], angle: float):
    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    rotated_image = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    rotated_labels = []
    for class_id, points in labels:
        pixel_points = points * np.array([width, height], dtype=np.float32)
        ones = np.ones((len(pixel_points), 1), dtype=np.float32)
        transformed = np.hstack([pixel_points, ones]) @ matrix.T
        transformed[:, 0] /= width
        transformed[:, 1] /= height
        rotated_labels.append((class_id, transformed.astype(np.float32)))

    return rotated_image, clean_labels(rotated_labels)


def change_brightness_contrast(image: np.ndarray, brightness: int = 0, contrast: float = 1.0) -> np.ndarray:
    # Poligon degismez; sadece piksel degerleri degisir.
    adjusted = image.astype(np.float32) * contrast + brightness
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def color_jitter(image: np.ndarray) -> np.ndarray:
    # BGR -> HSV ile renk tonu ve doygunlugu kontrollu degistiriyoruz.
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + HUE_SHIFT) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * SATURATION_SCALE, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def mask_protected_crop(image: np.ndarray, labels: list[tuple[int, np.ndarray]], rng: random.Random):
    height, width = image.shape[:2]
    crop_size = min(CROP_SIZE, width, height)

    if labels:
        all_points = np.vstack([points for _, points in labels])
        pixel_points = all_points * np.array([width, height], dtype=np.float32)
        x1, y1 = np.floor(pixel_points.min(axis=0)).astype(int)
        x2, y2 = np.ceil(pixel_points.max(axis=0)).astype(int)

        # Crop boyutu problemli bolgenin tamamini icine alacak kadar buyutulur.
        needed_size = max(x2 - x1, y2 - y1) + (2 * CROP_PADDING)
        crop_size = int(min(max(crop_size, needed_size), width, height))

        min_left = max(0, x2 - crop_size)
        max_left = min(x1, width - crop_size)
        min_top = max(0, y2 - crop_size)
        max_top = min(y1, height - crop_size)
    else:
        # Etiket yoksa merkezden crop almak yeterli.
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


def save_sample(output_root: Path, split: str, image_path: Path, suffix: str, image: np.ndarray, labels) -> None:
    output_image = output_root / "images" / split / f"{image_path.stem}_{suffix}{image_path.suffix}"
    output_label = output_root / "labels" / split / f"{image_path.stem}_{suffix}.txt"
    write_image(output_image, image)
    write_labels(output_label, labels)


def build_variations():
    variations = []

    for angle in ROTATION_ANGLES:
        variations.append(
            (
                f"rot_{angle:+g}",
                lambda image, labels, rng, angle=angle: rotate_image_and_labels(image, labels, angle),
            )
        )

    if USE_HORIZONTAL_FLIP:
        variations.append(("hflip", lambda image, labels, rng: (cv2.flip(image, 1), flip_labels(labels, True, False))))

    if USE_VERTICAL_FLIP:
        variations.append(("vflip", lambda image, labels, rng: (cv2.flip(image, 0), flip_labels(labels, False, True))))

    for brightness in BRIGHTNESS_VALUES:
        variations.append(
            (
                f"brightness_{brightness:+d}",
                lambda image, labels, rng, brightness=brightness: (
                    change_brightness_contrast(image, brightness=brightness),
                    labels,
                ),
            )
        )

    for contrast in CONTRAST_VALUES:
        variations.append(
            (
                f"contrast_{contrast:g}",
                lambda image, labels, rng, contrast=contrast: (
                    change_brightness_contrast(image, contrast=contrast),
                    labels,
                ),
            )
        )

    if USE_COLOR_JITTER:
        variations.append(("color_jitter", lambda image, labels, rng: (color_jitter(image), labels)))

    if USE_MASK_PROTECTED_CROP:
        variations.append(("mask_crop", lambda image, labels, rng: mask_protected_crop(image, labels, rng)))

    return variations


def choose_variations(variations, count: int, rng: random.Random):
    if count < 0:
        raise ValueError("--variations 0 veya daha buyuk olmali.")
    if count > len(variations):
        raise ValueError(
            f"--variations en fazla {len(variations)} olabilir. "
            "Daha fazla istiyorsan ustteki augmentation ayarlarina yeni secenek ekle."
        )
    if count == len(variations):
        return variations
    return rng.sample(variations, count)


def validate_variation_count(variations, count: int) -> None:
    if count < 0:
        raise ValueError("--variations 0 veya daha buyuk olmali.")
    if count > len(variations):
        raise ValueError(
            f"--variations en fazla {len(variations)} olabilir. "
            "Daha fazla istiyorsan ustteki augmentation ayarlarina yeni secenek ekle."
        )


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


def augment_dataset(input_root: Path, output_root: Path, overwrite: bool, variations_per_train_image: int) -> None:
    if input_root == output_root or input_root in output_root.parents or output_root in input_root.parents:
        raise ValueError("Cikti klasoru input klasoruyle ayni yerde veya onun icinde olamaz.")

    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"Cikti klasoru zaten var: {output_root}\nYeniden olusturmak icin --overwrite ekle.")
        shutil.rmtree(output_root)

    rng = random.Random(RANDOM_SEED)
    variations = build_variations()
    validate_variation_count(variations, variations_per_train_image)
    print(
        f"Varyasyon ayari: train icin base + {variations_per_train_image}; "
        f"val/test icin sadece base. Tum ciktilar {IMAGE_SIZE}x{IMAGE_SIZE}."
    )

    for split in SPLITS:
        image_dir = input_root / "images" / split
        label_dir = input_root / "labels" / split
        image_paths = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)

        for image_path in image_paths:
            label_path = label_dir / f"{image_path.stem}.txt"
            image = resize_to_training_size(read_image(image_path))
            labels = read_labels(label_path)

            # Orijinal ornek de 640x640 olarak cikti veri setine yazilir.
            save_sample(output_root, split, image_path, "base", image, labels)

            # Val/test setleri sadece olceklendirilir; augmentation sadece train icin yapilir.
            if split != "train":
                continue

            for suffix, apply_variation in choose_variations(variations, variations_per_train_image, rng):
                augmented_image, augmented_labels = apply_variation(image, labels, rng)
                save_sample(output_root, split, image_path, suffix, augmented_image, augmented_labels)

        print(f"{split}: {len(image_paths)} kaynak gorsel islendi.")

    write_data_yaml(output_root)
    print(f"Augmented YOLO veri seti hazir: {output_root}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLO segmentation veri setine kontrollu augmentation uygula.")
    parser.add_argument("--input", type=Path, default=INPUT_ROOT, help="PlantSeg -> YOLO cikti klasoru.")
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT, help="Augmented YOLO veri seti klasoru.")
    parser.add_argument("--overwrite", action="store_true", help="Cikti klasoru varsa silip yeniden olustur.")
    parser.add_argument(
        "--variations",
        type=int,
        default=VARIATIONS_PER_TRAIN_IMAGE,
        help="Her train gorseli icin base disinda uretilecek augmentation sayisi.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_root = args.input.resolve()
    output_root = args.output.resolve()

    if not input_root.exists():
        raise FileNotFoundError(
            f"YOLO veri seti bulunamadi: {input_root}\n"
            "Once PlantSeg -> YOLO donusumu icin src\\plantseg_to_yolo.py dosyasini calistir."
        )

    augment_dataset(
        input_root=input_root,
        output_root=output_root,
        overwrite=args.overwrite,
        variations_per_train_image=args.variations,
    )


if __name__ == "__main__":
    main()
