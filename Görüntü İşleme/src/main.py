from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
YOLO_DATASET_ROOT = ROOT / "data" / "plantseg_yolo_augmented"
DEFAULT_MODEL = "yolo26n-seg.pt"
TRAIN_OUTPUT = ROOT / "outputs" / "training"


def ensure_project_venv() -> None:
    if not VENV_PYTHON.exists():
        return

    current_python = Path(sys.executable).resolve()
    target_python = VENV_PYTHON.resolve()
    if current_python == target_python:
        return

    print(f"Yanlis Python kullanildi: {current_python}", flush=True)
    print(f"Proje sanal ortamina geciliyor: {target_python}", flush=True)
    result = subprocess.run([str(target_python), str(Path(__file__).resolve()), *sys.argv[1:]])
    raise SystemExit(result.returncode)


BatchValue = int | float
CacheValue = Literal[False, "ram", "disk"]


def parse_batch(value: str) -> BatchValue:
    normalized = value.strip().lower()
    if normalized == "auto":
        return -1

    try:
        batch = float(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Batch icin 'auto', tam sayi veya 0.0-1.0 arasi VRAM orani yaz."
        ) from exc

    if batch == -1:
        return -1
    if batch <= 0:
        raise argparse.ArgumentTypeError(
            "Batch pozitif olmali veya otomatik ayar icin 'auto' olmali."
        )
    if batch > 1 and not batch.is_integer():
        raise argparse.ArgumentTypeError(
            "Manuel batch 1'den buyukse tam sayi olmali; ornek: 8, 16."
        )

    return int(batch) if batch >= 1 else batch


def parse_cache(value: str) -> CacheValue:
    normalized = value.strip().lower()
    if normalized in {"false", "0", "no", "off", "none"}:
        return False
    if normalized in {"ram", "disk"}:
        return normalized
    raise argparse.ArgumentTypeError("Cache icin false, ram veya disk yaz.")


def train(
    data_yaml: Path,
    model_path: str,
    epochs: int,
    imgsz: int,
    batch: BatchValue,
    device: str,
    workers: int,
    patience: int,
    cache: CacheValue,
    deterministic: bool,
) -> None:
    from ultralytics import YOLO

    print("YOLO egitimi basliyor.")
    print(f"Data yaml: {data_yaml}")
    print(f"Model: {model_path}")
    print(
        f"Epochs: {epochs}, patience: {patience}, imgsz: {imgsz}, "
        f"batch: {batch}, device: {device}, workers: {workers}, cache: {cache}"
    )

    model = YOLO(str(model_path))
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        patience=patience,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        cache=cache,
        project=str(TRAIN_OUTPUT),
        name="plantseg_problem_region",
        exist_ok=True,
        plots=True,
        deterministic=deterministic,
    )


def find_data_yaml(data_path: Path) -> Path:
    if data_path.is_file():
        return data_path

    data_yaml = data_path / "data.yaml"
    if data_yaml.exists():
        return data_yaml

    raise FileNotFoundError(
        f"YOLO data yaml bulunamadi: {data_yaml}\n"
        "Once PlantSeg -> YOLO donusumunu, sonra augmentation adimini calistir:\n"
        ".venv\\Scripts\\python.exe src\\plantseg_to_yolo.py\n"
        ".venv\\Scripts\\python.exe src\\augment_yolo.py"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLO segmentation egitimini baslat.")
    parser.add_argument(
        "--data",
        type=Path,
        default=YOLO_DATASET_ROOT,
        help="YOLO data klasoru veya data.yaml dosyasi.",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Baslangic YOLO segmentation agirligi."
    )
    parser.add_argument("--epochs", type=int, default=300, help="Egitim epoch sayisi.")
    parser.add_argument(
        "--patience",
        type=int,
        default=30,
        help="Iyilesme yoksa kac epoch sonra early stopping yapilsin.",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO egitim gorsel boyutu.")
    parser.add_argument(
        "--batch",
        type=parse_batch,
        default=-1,
        help="Batch boyutu. 'auto' RTX 3070 VRAM'e gore secer; 0.7 gibi de VRAM orani verilebilir.",
    )
    parser.add_argument("--device", default="0", help="GPU icin 0, CPU icin cpu yaz.")
    parser.add_argument("--workers", type=int, default=4, help="Data loader worker sayisi.")
    parser.add_argument(
        "--cache",
        type=parse_cache,
        default=False,
        help="Dataloader cache modu: false, ram veya disk. 16 GB RAM icin varsayilan false.",
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Tekrarlanabilirlik icin deterministic modu ac. Biraz yavaslatabilir.",
    )
    return parser.parse_args()


def resolve_model_reference(model_value: str) -> str:
    model_path = Path(model_value)
    if model_path.exists():
        return str(model_path.resolve())

    if model_path.parent != Path("."):
        raise FileNotFoundError(f"Model dosyasi yok: {model_path}")

    return model_value


def main() -> None:
    args = parse_args()
    data_path = args.data.resolve()
    model_path = resolve_model_reference(args.model)

    if not data_path.exists():
        raise FileNotFoundError(
            f"YOLO veri yolu bulunamadi: {data_path}\n"
            "Once PlantSeg -> YOLO donusumunu, sonra augmentation adimini calistir:\n"
            ".venv\\Scripts\\python.exe src\\plantseg_to_yolo.py\n"
            ".venv\\Scripts\\python.exe src\\augment_yolo.py"
        )

    data_yaml = find_data_yaml(data_path)

    train(
        data_yaml=data_yaml,
        model_path=model_path,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        cache=args.cache,
        deterministic=args.deterministic,
    )


if __name__ == "__main__":
    ensure_project_venv()
    main()
