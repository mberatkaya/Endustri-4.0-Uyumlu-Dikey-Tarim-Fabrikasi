from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DEFAULT_DATA = ROOT / "data" / "plantseg_yolo_augmented" / "data.yaml"
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"
EVAL_OUTPUT = ROOT / "outputs" / "evaluation"


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


def find_latest_best_weights() -> Path:
    if DEFAULT_WEIGHTS.exists():
        return DEFAULT_WEIGHTS

    candidates = [path for path in (ROOT / "outputs" / "training").rglob("best.pt")]

    if not candidates and DEFAULT_WEIGHTS.exists():
        return DEFAULT_WEIGHTS

    if not candidates:
        candidates = [
            path
            for path in ROOT.rglob("best.pt")
            if ".venv" not in path.parts and "eski" not in path.parts
        ]
    if not candidates:
        raise FileNotFoundError(
            "best.pt bulunamadi. Once egitimi calistir veya --weights ile model yolunu ver."
        )

    return max(candidates, key=lambda path: path.stat().st_mtime)


def resolve_data_yaml(data_path: Path) -> Path:
    if data_path.is_file():
        return data_path

    data_yaml = data_path / "data.yaml"
    if data_yaml.exists():
        return data_yaml

    raise FileNotFoundError(f"data.yaml bulunamadi: {data_yaml}")


def get_metric(results_dict: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in results_dict:
            return results_dict[name]
    return None


def save_metrics_json(results: Any, output_dir: Path, weights: Path, data_yaml: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    results_dict = getattr(results, "results_dict", {}) or {}
    serializable = {
        "weights": str(weights),
        "data": str(data_yaml),
        "split": "test",
        "metrics": {
            key: float(value)
            for key, value in results_dict.items()
            if isinstance(value, (int, float))
        },
    }

    output_path = output_dir / "test_metrics_summary.json"
    output_path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def evaluate(
    weights: Path,
    data_yaml: Path,
    imgsz: int,
    batch: int,
    device: str,
    workers: int,
    iou: float,
    conf: float | None,
    save_json: bool,
) -> None:
    from ultralytics import YOLO

    print("Test degerlendirmesi basliyor.")
    print(f"Model: {weights}")
    print(f"Data yaml: {data_yaml}")
    print(f"Split: test, imgsz: {imgsz}, batch: {batch}, device: {device}, workers: {workers}")

    model = YOLO(str(weights))
    val_kwargs: dict[str, Any] = {
        "data": str(data_yaml),
        "split": "test",
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "workers": workers,
        "iou": iou,
        "project": str(EVAL_OUTPUT),
        "name": "best_on_test",
        "exist_ok": True,
        "plots": True,
        "save_json": save_json,
    }
    if conf is not None:
        val_kwargs["conf"] = conf

    results = model.val(**val_kwargs)

    results_dict = getattr(results, "results_dict", {}) or {}
    metrics_path = save_metrics_json(
        results=results,
        output_dir=EVAL_OUTPUT / "best_on_test",
        weights=weights,
        data_yaml=data_yaml,
    )

    box_map50 = get_metric(results_dict, ("metrics/mAP50(B)", "metrics/mAP50"))
    box_map5095 = get_metric(results_dict, ("metrics/mAP50-95(B)", "metrics/mAP50-95"))
    mask_map50 = get_metric(results_dict, ("metrics/mAP50(M)",))
    mask_map5095 = get_metric(results_dict, ("metrics/mAP50-95(M)",))

    print("\nOzet metrikler:")
    if box_map50 is not None:
        print(f"  Box mAP50:      {box_map50:.4f}")
    if box_map5095 is not None:
        print(f"  Box mAP50-95:   {box_map5095:.4f}")
    if mask_map50 is not None:
        print(f"  Mask mAP50:     {mask_map50:.4f}")
    if mask_map5095 is not None:
        print(f"  Mask mAP50-95:  {mask_map5095:.4f}")

    print(f"\nUltralytics ciktilari: {EVAL_OUTPUT / 'best_on_test'}")
    print(f"Metrik ozeti: {metrics_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="En iyi best.pt modelini test dataseti uzerinde degerlendir."
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help="best.pt yolu. Bos birakilirsa outputs/training altindaki en yeni best.pt kullanilir.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="YOLO data.yaml dosyasi veya data.yaml iceren dataset klasoru.",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Degerlendirme gorsel boyutu.")
    parser.add_argument("--batch", type=int, default=8, help="Degerlendirme batch boyutu.")
    parser.add_argument("--device", default="0", help="GPU icin 0, CPU icin cpu yaz.")
    parser.add_argument("--workers", type=int, default=4, help="Data loader worker sayisi.")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU esigi.")
    parser.add_argument(
        "--conf", type=float, default=None, help="Confidence esigi. Varsayilan Ultralytics ayari."
    )
    parser.add_argument("--save-json", action="store_true", help="COCO JSON metrik dosyasi yaz.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    weights = args.weights.resolve() if args.weights else find_latest_best_weights()
    data_yaml = resolve_data_yaml(args.data.resolve())

    if not weights.exists():
        raise FileNotFoundError(f"Model dosyasi bulunamadi: {weights}")
    if not data_yaml.exists():
        raise FileNotFoundError(f"Data yaml bulunamadi: {data_yaml}")

    evaluate(
        weights=weights,
        data_yaml=data_yaml,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        iou=args.iou,
        conf=args.conf,
        save_json=args.save_json,
    )


if __name__ == "__main__":
    ensure_project_venv()
    main()
