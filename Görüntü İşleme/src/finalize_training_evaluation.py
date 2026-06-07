from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DEFAULT_RUN_DIR = ROOT / "outputs" / "training" / "plantseg_problem_region"
DEFAULT_DATA = ROOT / "data" / "plantseg_yolo_augmented" / "data.yaml"


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


def resolve_weights(run_dir: Path, requested: Path | None) -> Path:
    if requested is not None:
        weights = requested
    else:
        weights = run_dir / "weights" / "best.pt"
        if not weights.exists():
            weights = run_dir / "weights" / "last.pt"

    weights = weights.resolve()
    if not weights.exists():
        raise FileNotFoundError(f"Model agirligi bulunamadi: {weights}")
    return weights


def preserve_file(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def restore_file(path: Path, content: bytes | None) -> None:
    if content is None:
        return
    path.write_bytes(content)


def save_metrics_summary(results: Any, run_dir: Path, weights: Path, data_yaml: Path, split: str) -> Path:
    results_dict = getattr(results, "results_dict", {}) or {}
    payload = {
        "weights": str(weights),
        "data": str(data_yaml),
        "split": split,
        "metrics": {
            key: float(value)
            for key, value in results_dict.items()
            if isinstance(value, (int, float))
        },
    }
    output_path = run_dir / f"{split}_metrics_summary.json"
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def plot_results_csv(run_dir: Path) -> Path | None:
    results_csv = run_dir / "results.csv"
    if not results_csv.exists():
        return None

    try:
        from ultralytics.utils.plotting import plot_results

        plot_results(file=str(results_csv))
        output_path = run_dir / "results.png"
        if output_path.exists():
            return output_path
    except Exception as exc:
        print(f"Ultralytics results grafikleri cizilemedi, matplotlib deneniyor: {exc}", flush=True)

    import matplotlib.pyplot as plt
    import pandas as pd

    data = pd.read_csv(results_csv)
    data.columns = [column.strip() for column in data.columns]
    epoch = data["epoch"] if "epoch" in data.columns else range(len(data))
    columns = [
        "train/box_loss",
        "train/seg_loss",
        "train/cls_loss",
        "train/dfl_loss",
        "metrics/mAP50(B)",
        "metrics/mAP50-95(B)",
        "metrics/mAP50(M)",
        "metrics/mAP50-95(M)",
        "val/box_loss",
        "val/seg_loss",
        "val/cls_loss",
        "val/dfl_loss",
    ]
    present_columns = [column for column in columns if column in data.columns]
    if not present_columns:
        return None

    fig, axes = plt.subplots(3, 4, figsize=(16, 10), constrained_layout=True)
    for axis, column in zip(axes.ravel(), present_columns):
        axis.plot(epoch, data[column], linewidth=1.8)
        axis.set_title(column)
        axis.set_xlabel("epoch")
        axis.grid(True, alpha=0.25)

    for axis in axes.ravel()[len(present_columns) :]:
        axis.axis("off")

    output_path = run_dir / "results.png"
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def run_validation(
    run_dir: Path,
    weights: Path,
    data_yaml: Path,
    split: str,
    imgsz: int,
    batch: int,
    device: str,
    workers: int,
    iou: float,
) -> Path:
    from ultralytics import YOLO

    print("Eksik egitim degerlendirme dosyalari uretiliyor.", flush=True)
    print(f"Run klasoru: {run_dir}", flush=True)
    print(f"Model: {weights}", flush=True)
    print(f"Data yaml: {data_yaml}", flush=True)
    print(f"Split: {split}, imgsz: {imgsz}, batch: {batch}, device: {device}", flush=True)

    args_yaml = run_dir / "args.yaml"
    original_args = preserve_file(args_yaml)

    model = YOLO(str(weights))
    results = model.val(
        data=str(data_yaml),
        split=split,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        iou=iou,
        project=str(run_dir.parent),
        name=run_dir.name,
        exist_ok=True,
        plots=True,
        save_json=False,
    )

    restore_file(args_yaml, original_args)
    metrics_path = save_metrics_summary(results, run_dir, weights, data_yaml, split)
    print(f"Metrik ozeti yazildi: {metrics_path}", flush=True)
    return metrics_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Yarida kesilen YOLO egitim klasorundeki degerlendirme dosyalarini tamamla.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR, help="YOLO egitim run klasoru.")
    parser.add_argument("--weights", type=Path, default=None, help="Degerlendirilecek .pt dosyasi. Varsayilan best.pt.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="YOLO data.yaml dosyasi.")
    parser.add_argument("--split", default="val", choices=("train", "val", "test"), help="Degerlendirilecek split.")
    parser.add_argument("--imgsz", type=int, default=640, help="Degerlendirme gorsel boyutu.")
    parser.add_argument("--batch", type=int, default=8, help="Degerlendirme batch boyutu.")
    parser.add_argument("--device", default="0", help="GPU icin 0, CPU icin cpu yaz.")
    parser.add_argument("--workers", type=int, default=4, help="Data loader worker sayisi.")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU esigi.")
    parser.add_argument("--skip-val", action="store_true", help="Sadece results.png uret.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    data_yaml = args.data.resolve()
    weights = resolve_weights(run_dir, args.weights.resolve() if args.weights else None)

    if not run_dir.exists():
        raise FileNotFoundError(f"Run klasoru bulunamadi: {run_dir}")
    if not data_yaml.exists():
        raise FileNotFoundError(f"Data yaml bulunamadi: {data_yaml}")

    if not args.skip_val:
        run_validation(
            run_dir=run_dir,
            weights=weights,
            data_yaml=data_yaml,
            split=args.split,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            iou=args.iou,
        )

    results_png = plot_results_csv(run_dir)
    if results_png is not None:
        print(f"Egitim grafigi yazildi: {results_png}", flush=True)

    print("Tamamlandi.", flush=True)


if __name__ == "__main__":
    ensure_project_venv()
    main()
