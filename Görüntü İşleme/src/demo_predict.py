from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"
WINDOW_NAME = "PlantSeg problem_region tahmini"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


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


ensure_project_venv()

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from ultralytics import YOLO  # noqa: E402


def read_image(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Resim okunamadi: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix, image)
    if not ok:
        raise ValueError(f"Resim yazilamadi: {path}")
    encoded.tofile(str(path))


def parse_source(value: str) -> int | Path:
    if value.isdigit():
        return int(value)
    return Path(value)


def predict_frame(model: YOLO, frame: np.ndarray, conf: float, imgsz: int) -> np.ndarray:
    results = model.predict(frame, conf=conf, imgsz=imgsz, verbose=False)
    return results[0].plot()


def show_image(model: YOLO, image_path: Path, conf: float, imgsz: int, output: Path | None) -> None:
    image = read_image(image_path)
    prediction = predict_frame(model, image, conf=conf, imgsz=imgsz)

    if output is not None:
        write_image(output, prediction)
        print(f"Tahmin gorseli yazildi: {output}")
        return

    cv2.imshow(WINDOW_NAME, prediction)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def show_video_or_webcam(
    model: YOLO,
    source: str | int,
    conf: float,
    imgsz: int,
    output: Path | None,
    max_frames: int | None,
) -> None:
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise FileNotFoundError(f"Video/webcam acilamadi: {source}")

    writer: cv2.VideoWriter | None = None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))

    frame_count = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break

        prediction = predict_frame(model, frame, conf=conf, imgsz=imgsz)
        if writer is not None:
            writer.write(prediction)
        else:
            cv2.imshow(WINDOW_NAME, prediction)
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):
                break

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            break

    capture.release()
    if writer is not None:
        writer.release()
        print(f"Tahmin videosu yazildi: {output}")
    else:
        cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PlantSeg problem_region YOLO tahmini calistir.")
    parser.add_argument("--source", required=True, help="Resim/video yolu. Webcam icin 0 yaz.")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS, help="Model agirligi yolu.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence esigi.")
    parser.add_argument("--imgsz", type=int, default=640, help="Tahmin gorsel boyutu.")
    parser.add_argument("--output", type=Path, default=None, help="Tahmini resim/video olarak kaydet.")
    parser.add_argument("--max-frames", type=int, default=None, help="Video icin en fazla islenecek kare sayisi.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights = args.weights.resolve()
    if not weights.exists():
        raise FileNotFoundError(f"Model bulunamadi: {weights}")

    model = YOLO(str(weights))
    source = parse_source(args.source)

    if isinstance(source, int):
        show_video_or_webcam(
            model=model,
            source=source,
            conf=args.conf,
            imgsz=args.imgsz,
            output=args.output,
            max_frames=args.max_frames,
        )
        return

    source_path = source.resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Kaynak bulunamadi: {source_path}")

    if source_path.suffix.lower() in IMAGE_EXTENSIONS:
        show_image(model, source_path, conf=args.conf, imgsz=args.imgsz, output=args.output)
        return

    show_video_or_webcam(
        model=model,
        source=str(source_path),
        conf=args.conf,
        imgsz=args.imgsz,
        output=args.output,
        max_frames=args.max_frames,
    )


if __name__ == "__main__":
    main()
