from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

PLANT_COLUMN = "Plant_ID"
DATE_COLUMN = "Date"
TARGET_COLUMN = "Growth Days"
BASE_FEATURES = (
    "Temperature (°C)",
    "Humidity (%)",
    "pH Level",
    "TDS Value (ppm)",
)
DEFAULT_LAGS = (1, 2, 3, 7)


def load_dataset(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="latin-1")
    frame[DATE_COLUMN] = pd.to_datetime(frame[DATE_COLUMN])
    return frame


def create_lagged_features(
    frame: pd.DataFrame,
    lags: tuple[int, ...] = DEFAULT_LAGS,
    rolling_window: int = 7,
) -> pd.DataFrame:
    required = {PLANT_COLUMN, DATE_COLUMN, *BASE_FEATURES}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Eksik model sütunları: {sorted(missing)}")

    result = frame.copy()
    result[DATE_COLUMN] = pd.to_datetime(result[DATE_COLUMN])
    result = result.sort_values([PLANT_COLUMN, DATE_COLUMN]).reset_index(drop=True)

    for feature in BASE_FEATURES:
        grouped = result.groupby(PLANT_COLUMN)[feature]
        for lag in lags:
            result[f"{feature} Lag {lag}"] = grouped.shift(lag)
        result[f"{feature} Rolling Mean"] = grouped.transform(
            lambda values: values.rolling(rolling_window).mean()
        )
        result[f"{feature} Rolling Std"] = grouped.transform(
            lambda values: values.rolling(rolling_window).std()
        )

    result["Day of Week"] = result[DATE_COLUMN].dt.dayofweek + 1
    result["Month"] = result[DATE_COLUMN].dt.month
    return result


def prepare_training_data(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    if TARGET_COLUMN not in frame:
        raise ValueError(f"Hedef sütunu bulunamadı: {TARGET_COLUMN}")
    featured = create_lagged_features(frame).dropna()
    features = featured.drop(columns=[TARGET_COLUMN, PLANT_COLUMN, DATE_COLUMN])
    target = featured[TARGET_COLUMN]
    return features, target


def build_model(**overrides) -> XGBRegressor:
    parameters = {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "objective": "reg:squarederror",
        "random_state": 42,
        "n_jobs": 1,
    }
    parameters.update(overrides)
    return XGBRegressor(**parameters)


def train_model(
    features: pd.DataFrame,
    target: pd.Series,
    **model_overrides,
) -> XGBRegressor:
    model = build_model(**model_overrides)
    model.fit(features, target)
    return model


def evaluate_predictions(
    expected: pd.Series | np.ndarray,
    predicted: np.ndarray,
) -> dict[str, float]:
    mse = mean_squared_error(expected, predicted)
    return {
        "mae": float(mean_absolute_error(expected, predicted)),
        "mse": float(mse),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(expected, predicted)),
    }


def train_and_evaluate(
    frame: pd.DataFrame,
    test_size: float = 0.2,
    **model_overrides,
) -> tuple[XGBRegressor, dict[str, float]]:
    features, target = prepare_training_data(frame)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=42,
    )
    model = train_model(x_train, y_train, **model_overrides)
    metrics = evaluate_predictions(y_test, model.predict(x_test))
    return model, metrics


def predict_harvest_days(
    model: XGBRegressor,
    features: pd.DataFrame,
    total_growth_days: int = 45,
) -> np.ndarray:
    predicted_growth_days = model.predict(features)
    return np.clip(total_growth_days - predicted_growth_days, 0, None)
