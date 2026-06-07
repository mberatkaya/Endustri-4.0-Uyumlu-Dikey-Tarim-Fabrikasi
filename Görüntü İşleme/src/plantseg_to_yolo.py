from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
PLANTSEG_ROOT = ROOT / "data" / "plantseg" / "plantseg"
OUTPUT_ROOT = ROOT / "data" / "plantseg_yolo"

SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def read_mask(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    mask = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise ValueError(f"Mask okunamadi: {path}")
    return mask


def find_image(dataset_root: Path, split: str, stem: str) -> Path:
    image_dir = dataset_root / "images" / split
    for extension in IMAGE_EXTENSIONS:
        image_path = image_dir / f"{stem}{extension}"
        if image_path.exists():
            return image_path
    raise FileNotFoundError(f"Gorsel bulunamadi: {image_dir / stem}")


def contour_to_yolo_line(contour: np.ndarray, width: int, height: int, epsilon: float) -> str | None:
    simplified = cv2.approxPolyDP(contour, epsilon * cv2.arcLength(contour, True), True)
    points = simplified.reshape(-1, 2)
    if len(points) < 3:
        return None

    values = ["0"]
    for x, y in points:
        values.append(f"{min(max(x / width, 0), 1):.6f}")
        values.append(f"{min(max(y / height, 0), 1):.6f}")
    return " ".join(values)


def mask_to_yolo_lines(mask: np.ndarray, min_area: float, epsilon: float) -> list[str]:
    problem_mask = (mask > 0).astype(np.uint8)
    height, width = problem_mask.shape
    contours, _ = cv2.findContours(problem_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    lines: list[str] = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        line = contour_to_yolo_line(contour, width, height, epsilon)
        if line:
            lines.append(line)
    return lines


def copy_image(source: Path, output_root: Path, split: str) -> None:
    target = output_root / "images" / split / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_data_yaml(output_root: Path) -> Path:
    yaml_path = output_root / "data.yaml"
    data = {
        "path": output_root.as_posix(),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "problem_region"},
    }
    yaml_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )
    return yaml_path


def paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def convert_plantseg_to_yolo(
    plantseg_root: Path,
    output_root: Path,
    min_area: float,
    epsilon: float,
    overwrite: bool,
) -> None:
    if paths_overlap(plantseg_root, output_root):
        raise ValueError("Cikti klasoru orijinal PlantSeg klasoruyle ayni yerde veya onun icinde olamaz.")

    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"Cikti klasoru zaten var: {output_root}\nYeniden olusturmak icin --overwrite ekle.")
        shutil.rmtree(output_root)

    print("PlantSeg -> YOLO donusumu basladi.")
    print(f"Kaynak PlantSeg klasoru: {plantseg_root}")
    print(f"Yeni YOLO klasoru: {output_root}")

    for split in SPLITS:
        annotation_dir = plantseg_root / "annotations" / split
        label_dir = output_root / "labels" / split
        label_dir.mkdir(parents=True, exist_ok=True)

        masks = sorted(annotation_dir.glob("*.png"))
        empty_count = 0

        for mask_path in masks:
            image_path = find_image(plantseg_root, split, mask_path.stem)
            copy_image(image_path, output_root, split)

            mask = read_mask(mask_path)
            lines = mask_to_yolo_lines(mask, min_area=min_area, epsilon=epsilon)

            label_path = label_dir / f"{mask_path.stem}.txt"
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            empty_count += int(not lines)

        print(f"{split}: {len(masks)} label uretildi, {empty_count} bos label")

    yaml_path = write_data_yaml(output_root)
    print(f"YOLO data yaml hazir: {yaml_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PlantSeg maskelerini YOLO segmentation formatina cevir.")
    parser.add_argument("--plantseg", type=Path, default=PLANTSEG_ROOT, help="Orijinal PlantSeg klasoru.")
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT, help="Olusturulacak YOLO veri seti klasoru.")
    parser.add_argument("--min-area", type=float, default=10.0, help="Cok kucuk konturlari elemek icin alan esigi.")
    parser.add_argument("--epsilon", type=float, default=0.002, help="Polygon sadelestirme katsayisi.")
    parser.add_argument("--overwrite", action="store_true", help="Cikti klasoru varsa silip yeniden olustur.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plantseg_root = args.plantseg.resolve()
    output_root = args.output.resolve()

    if not plantseg_root.exists():
        raise FileNotFoundError(f"PlantSeg klasoru yok: {plantseg_root}")
    convert_plantseg_to_yolo(
        plantseg_root=plantseg_root,
        output_root=output_root,
        min_area=args.min_area,
        epsilon=args.epsilon,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
