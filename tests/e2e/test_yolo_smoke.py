from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.e2e
@pytest.mark.yolo
def test_trained_yolo_model_cpu_smoke():
    if os.getenv("RUN_YOLO_SMOKE") != "1":
        pytest.skip("YOLO smoke testi yalnızca staging workflow'unda çalışır.")

    from ultralytics import YOLO

    project_root = Path(__file__).resolve().parents[2]
    model_path = project_root / "Görüntü İşleme" / "models" / "best.pt"
    model = YOLO(str(model_path))
    image = np.zeros((64, 64, 3), dtype=np.uint8)

    results = model.predict(image, imgsz=64, device="cpu", verbose=False)

    assert len(results) == 1
