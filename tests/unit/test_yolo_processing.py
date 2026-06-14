from __future__ import annotations

from unittest.mock import Mock

import numpy as np
from demo_predict import parse_source, predict_frame


def test_parse_source_supports_webcam_and_file():
    assert parse_source("0") == 0
    assert parse_source("image.jpg").name == "image.jpg"


def test_predict_frame_uses_model_result_plot():
    expected = np.ones((32, 32, 3), dtype=np.uint8)
    result = Mock()
    result.plot.return_value = expected
    model = Mock()
    model.predict.return_value = [result]

    actual = predict_frame(
        model,
        np.zeros((32, 32, 3), dtype=np.uint8),
        conf=0.25,
        imgsz=64,
    )

    assert actual is expected
    model.predict.assert_called_once()
