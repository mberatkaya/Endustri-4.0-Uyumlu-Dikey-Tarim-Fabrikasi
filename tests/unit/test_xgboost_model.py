from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from harvest_model import (
    BASE_FEATURES,
    create_lagged_features,
    evaluate_predictions,
    predict_harvest_days,
    prepare_training_data,
    train_model,
)


def make_growth_data(days_per_plant: int = 16) -> pd.DataFrame:
    rows = []
    for plant_id in (1, 2, 3):
        for day in range(1, days_per_plant + 1):
            rows.append(
                {
                    "Plant_ID": plant_id,
                    "Date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=day - 1),
                    "Temperature (°C)": 20 + (day * 0.1) + plant_id,
                    "Humidity (%)": 60 + day,
                    "TDS Value (ppm)": 450 + (day * 4),
                    "pH Level": 5.5 + (day * 0.02),
                    "Growth Days": day,
                }
            )
    return pd.DataFrame(rows)


def test_lagged_features_are_calculated_per_plant():
    featured = create_lagged_features(make_growth_data())
    plant_two_first_row = featured[featured["Plant_ID"] == 2].iloc[0]

    assert pd.isna(plant_two_first_row["Temperature (°C) Lag 1"])
    assert "Temperature (°C) Rolling Mean" in featured
    assert "Day of Week" in featured
    assert "Month" in featured


def test_lagged_features_validate_columns():
    with pytest.raises(ValueError, match="Eksik model"):
        create_lagged_features(pd.DataFrame({"Plant_ID": [1]}))


def test_prepare_training_data_returns_numeric_contract():
    features, target = prepare_training_data(make_growth_data())

    assert not features.empty
    assert len(features) == len(target)
    assert not {"Plant_ID", "Date", "Growth Days"}.intersection(features.columns)
    assert all(feature in features.columns for feature in BASE_FEATURES)


def test_real_xgboost_training_and_harvest_prediction():
    features, target = prepare_training_data(make_growth_data(20))
    model = train_model(
        features,
        target,
        n_estimators=8,
        max_depth=2,
        learning_rate=0.2,
    )

    growth_predictions = model.predict(features)
    harvest_predictions = predict_harvest_days(model, features)
    metrics = evaluate_predictions(target, growth_predictions)

    assert len(harvest_predictions) == len(features)
    assert np.all(harvest_predictions >= 0)
    assert set(metrics) == {"mae", "mse", "rmse", "r2"}
    assert metrics["mae"] >= 0
