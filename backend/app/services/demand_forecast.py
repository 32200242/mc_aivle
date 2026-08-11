from __future__ import annotations

import copy
import math
import os
from bisect import bisect_right
from functools import lru_cache
from statistics import mean
from typing import Any, Callable, Iterator


MIN_HISTORY = 112
CV_FOLDS = 3
CV_HORIZON = 28
BOOST_ROUNDS = 40
ENSEMBLE_NAME = "검증가중 앙상블(Ridge+Boost+계절)"

np = None
XGBRegressor = None
if os.getenv("FORECAST_ENGINE", "native").lower() == "xgboost":
    try:  # Optional production engine; kept lazy so normal API startup stays fast.
        import numpy as np
        from xgboost import XGBRegressor
    except Exception:  # pragma: no cover - exercised only with optional wheels.
        np = None
        XGBRegressor = None


def _safe_mean(values: list[float], fallback: float = 0.0) -> float:
    return mean(values) if values else fallback


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Small Gaussian-elimination solver so the fallback has no heavy ML dependency."""
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            continue
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    current - factor * base
                    for current, base in zip(augmented[row], augmented[column], strict=True)
                ]
    return [augmented[index][-1] for index in range(size)]


def _features(series: list[float], index: int, baseline: float) -> list[float]:
    day = index % 7
    year_angle = 2 * math.pi * index / 365.25
    week_angle = 2 * math.pi * day / 7
    return [
        1.0,
        index / max(365.0, len(series)),
        math.sin(week_angle),
        math.cos(week_angle),
        math.sin(year_angle),
        math.cos(year_angle),
        series[index - 1] / baseline,
        series[index - 7] / baseline,
        series[index - 14] / baseline,
        series[index - 28] / baseline,
        _safe_mean(series[index - 7:index]) / baseline,
        _safe_mean(series[index - 28:index]) / baseline,
    ]


def _training_matrix(series: list[float]) -> tuple[list[list[float]], list[float], float]:
    baseline = max(1.0, _safe_mean(series, 1.0))
    rows = [_features(series, index, baseline) for index in range(28, len(series))]
    targets = [series[index] / baseline for index in range(28, len(series))]
    return rows, targets, baseline


def _ridge_fit(series: list[float], ridge: float = 0.8) -> tuple[list[float], float]:
    rows, targets, baseline = _training_matrix(series)
    feature_count = len(rows[0])
    matrix = [[0.0] * feature_count for _ in range(feature_count)]
    vector = [0.0] * feature_count
    for row, target in zip(rows, targets, strict=True):
        for left in range(feature_count):
            vector[left] += row[left] * target
            for right in range(feature_count):
                matrix[left][right] += row[left] * row[right]
    for index in range(1, feature_count):
        matrix[index][index] += ridge
    return _solve_linear(matrix, vector), baseline


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _ridge_forecast(series: list[float], horizon: int) -> list[float]:
    history = series[:]
    coefficients, baseline = _ridge_fit(history)
    result: list[float] = []
    for _ in range(horizon):
        estimate = max(0.0, _dot(coefficients, _features(history, len(history), baseline)) * baseline)
        result.append(estimate)
        history.append(estimate)
    return result


def _seasonal_naive(history: list[float], _: int) -> float:
    return history[-7] if len(history) >= 7 else history[-1]


def _weekday_average(history: list[float], _: int) -> float:
    return _safe_mean(history[-28::7], _safe_mean(history[-7:], history[-1]))


def _recursive_simple(
    series: list[float], horizon: int, predictor: Callable[[list[float], int], float]
) -> list[float]:
    history = series[:]
    result: list[float] = []
    for _ in range(horizon):
        estimate = max(0.0, predictor(history, len(history)))
        result.append(estimate)
        history.append(estimate)
    return result


def _native_boost_fit(series: list[float]) -> dict[str, Any]:
    """Deterministic gradient boosting with shallow regression stumps.

    This is a dependency-free fallback for local demos. Production installs can
    transparently replace it with XGBoost through requirements-forecast.txt.
    """
    rows, targets, baseline = _training_matrix(series)
    base = _safe_mean(targets, 1.0)
    fitted = [base] * len(targets)
    stumps: list[tuple[int, float, float, float]] = []
    learning_rate = 0.08
    minimum_leaf = max(8, len(rows) // 35)
    feature_splits: list[tuple[int, tuple[int, ...], dict[int, float]]] = []
    for feature_index in range(1, len(rows[0])):
        ordered_indices = tuple(sorted(range(len(rows)), key=lambda index: rows[index][feature_index]))
        ordered = [rows[index][feature_index] for index in ordered_indices]
        thresholds = {
            ordered[min(len(ordered) - 1, round((len(ordered) - 1) * quantile / 10))]
            for quantile in range(1, 10)
        }
        splits: dict[int, float] = {}
        for threshold in thresholds:
            split_count = bisect_right(ordered, threshold)
            if minimum_leaf <= split_count <= len(rows) - minimum_leaf:
                splits[split_count] = threshold
        if splits:
            feature_splits.append((feature_index, ordered_indices, splits))

    for _ in range(BOOST_ROUNDS):
        residuals = [target - estimate for target, estimate in zip(targets, fitted, strict=True)]
        total_sum = sum(residuals)
        total_square = sum(value * value for value in residuals)
        best: tuple[float, int, float, float, float] | None = None
        for feature_index, ordered_indices, splits in feature_splits:
            left_sum = left_square = 0.0
            for split_count, row_index in enumerate(ordered_indices, start=1):
                residual = residuals[row_index]
                left_sum += residual
                left_square += residual * residual
                threshold = splits.get(split_count)
                if threshold is None:
                    continue
                right_count = len(rows) - split_count
                right_sum = total_sum - left_sum
                left_value = left_sum / split_count
                right_value = right_sum / right_count
                loss = left_square - left_sum * left_sum / split_count
                loss += total_square - left_square - right_sum * right_sum / right_count
                candidate = (loss, feature_index, threshold, left_value, right_value)
                if best is None or candidate[0] < best[0]:
                    best = candidate
        if best is None:
            break
        _, feature_index, threshold, left_value, right_value = best
        left_step = left_value * learning_rate
        right_step = right_value * learning_rate
        stumps.append((feature_index, threshold, left_step, right_step))
        for index, row in enumerate(rows):
            fitted[index] += left_step if row[feature_index] <= threshold else right_step
    return {"baseline": baseline, "base": base, "stumps": stumps}


def _native_boost_predict(model: dict[str, Any], row: list[float]) -> float:
    estimate = float(model["base"])
    for feature_index, threshold, left_step, right_step in model["stumps"]:
        estimate += left_step if row[feature_index] <= threshold else right_step
    return estimate * float(model["baseline"])


def _native_boost_forecast(series: list[float], horizon: int) -> list[float]:
    history = series[:]
    model = _native_boost_fit(history)
    result: list[float] = []
    for _ in range(horizon):
        estimate = max(0.0, _native_boost_predict(model, _features(history, len(history), model["baseline"])))
        result.append(estimate)
        history.append(estimate)
    return result


def _xgboost_forecast(series: list[float], horizon: int) -> list[float]:
    if XGBRegressor is None or np is None:
        return _native_boost_forecast(series, horizon)
    rows, targets, baseline = _training_matrix(series)
    model = XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        n_estimators=180,
        max_depth=3,
        learning_rate=0.04,
        min_child_weight=6,
        subsample=0.85,
        colsample_bytree=0.9,
        reg_lambda=1.5,
        reg_alpha=0.05,
        random_state=20260803,
        n_jobs=1,
    )
    model.fit(np.asarray(rows, dtype=float), np.asarray(targets, dtype=float), verbose=False)
    history = series[:]
    result: list[float] = []
    for _ in range(horizon):
        row = np.asarray([_features(history, len(history), baseline)], dtype=float)
        estimate = max(0.0, float(model.predict(row)[0]) * baseline)
        result.append(estimate)
        history.append(estimate)
    return result


def _candidate_metrics(actual: list[float], predicted: list[float]) -> tuple[float, float]:
    errors = [abs(value - estimate) for value, estimate in zip(actual, predicted, strict=True)]
    mape_values = [
        abs(value - estimate) / value
        for value, estimate in zip(actual, predicted, strict=True)
        if value > 0
    ]
    return _safe_mean(errors), _safe_mean(mape_values) * 100


def _weight_vectors(model_count: int, units: int = 20) -> Iterator[list[float]]:
    def compositions(remaining: int, slots: int, prefix: list[int]) -> Iterator[list[int]]:
        if slots == 1:
            yield prefix + [remaining]
            return
        for value in range(remaining + 1):
            yield from compositions(remaining - value, slots - 1, prefix + [value])

    for vector in compositions(units, model_count, []):
        yield [value / units for value in vector]


def _optimize_weights(
    actual: list[float], predictions: dict[str, list[float]]
) -> tuple[dict[str, float], list[float]]:
    names = list(predictions)
    best_weights: list[float] | None = None
    best_prediction: list[float] = []
    best_key = (float("inf"), float("inf"))
    for weights in _weight_vectors(len(names)):
        combined = [
            sum(weights[index] * predictions[name][row] for index, name in enumerate(names))
            for row in range(len(actual))
        ]
        mae, _ = _candidate_metrics(actual, combined)
        concentration = sum(weight * weight for weight in weights)
        key = (mae, concentration)
        if key < best_key:
            best_key = key
            best_weights = weights
            best_prediction = combined
    assert best_weights is not None
    return {name: round(weight, 3) for name, weight in zip(names, best_weights, strict=True)}, best_prediction


def select_and_forecast(series: list[int], horizon: int = 28) -> dict[str, object]:
    return copy.deepcopy(_select_and_forecast_cached(tuple(series), horizon))


@lru_cache(maxsize=64)
def _select_and_forecast_cached(series: tuple[int, ...], horizon: int) -> dict[str, object]:
    values = [float(value) for value in series]
    if len(values) < MIN_HISTORY:
        base = round(_safe_mean(values[-7:], 0.0), 1)
        return {
            "selected_model": "최근 4주 동일요일 평균",
            "validation_days": 0,
            "cv_folds": 0,
            "mae": 0.0,
            "mape": 0.0,
            "engine": "fallback",
            "ensemble_weights": {},
            "interval_method": "±20% fallback",
            "leaderboard": [],
            "forecast": [base] * horizon,
            "lower": [max(0.0, base * 0.8)] * horizon,
            "upper": [base * 1.2] * horizon,
        }

    boost_name = "XGBoost(비선형·시차)" if XGBRegressor is not None else "내장 Gradient Boosting(비선형·시차)"
    candidates: dict[str, Callable[[list[float], int], list[float]]] = {
        "요일 계절 나이브": lambda history, steps: _recursive_simple(history, steps, _seasonal_naive),
        "최근 4주 동일요일 평균": lambda history, steps: _recursive_simple(history, steps, _weekday_average),
        "Ridge(추세·계절·시차)": _ridge_forecast,
        boost_name: _xgboost_forecast,
    }
    fold_count = min(CV_FOLDS, max(1, (len(values) - 56) // CV_HORIZON))
    first_train_end = len(values) - fold_count * CV_HORIZON
    fold_actuals: list[list[float]] = []
    fold_predictions: list[dict[str, list[float]]] = []
    for fold in range(fold_count):
        train_end = first_train_end + fold * CV_HORIZON
        fold_actual = values[train_end:train_end + CV_HORIZON]
        fold_actuals.append(fold_actual)
        history = values[:train_end]
        predictions: dict[str, list[float]] = {}
        for name, predictor in candidates.items():
            predictions[name] = predictor(history, len(fold_actual))
        fold_predictions.append(predictions)

    # 마지막 폴드는 가중치 조정에 사용하지 않고 독립 평가용으로 남긴다.
    evaluation_actual = fold_actuals[-1]
    evaluation_predictions = fold_predictions[-1]
    if fold_count > 1:
        tuning_actual = [value for fold_values in fold_actuals[:-1] for value in fold_values]
        tuning_predictions = {
            name: [value for predictions in fold_predictions[:-1] for value in predictions[name]]
            for name in candidates
        }
        weights, ensemble_tuning = _optimize_weights(tuning_actual, tuning_predictions)
        selection_results: list[dict[str, float | str]] = []
        for name, predictions in tuning_predictions.items():
            mae, mape = _candidate_metrics(tuning_actual, predictions)
            selection_results.append({"model": name, "mae": round(mae, 2), "mape": round(mape, 2)})
        ensemble_mae, ensemble_mape = _candidate_metrics(tuning_actual, ensemble_tuning)
        selection_results.append({"model": ENSEMBLE_NAME, "mae": round(ensemble_mae, 2), "mape": round(ensemble_mape, 2)})
        selection_results.sort(key=lambda item: (float(item["mae"]), 0 if item["model"] == ENSEMBLE_NAME else 1))
        selected_name = str(selection_results[0]["model"])
    else:
        equal_weight = round(1.0 / len(candidates), 3)
        weights = {name: equal_weight for name in candidates}
        last_name = next(reversed(candidates))
        weights[last_name] = round(
            1.0 - sum(value for name, value in weights.items() if name != last_name), 3
        )
        # 검증 구간이 하나뿐이면 미리 정한 동일가중 앙상블을 평가한다.
        selected_name = ENSEMBLE_NAME
        selection_results = []

    ensemble_validation = [
        sum(weights[name] * evaluation_predictions[name][index] for name in candidates)
        for index in range(len(evaluation_actual))
    ]
    if fold_count == 1:
        ensemble_mae, ensemble_mape = _candidate_metrics(evaluation_actual, ensemble_validation)
        selection_results.append({"model": ENSEMBLE_NAME, "mae": round(ensemble_mae, 2), "mape": round(ensemble_mape, 2)})
        for name, predictions in evaluation_predictions.items():
            mae, mape = _candidate_metrics(evaluation_actual, predictions)
            selection_results.append({"model": name, "mae": round(mae, 2), "mape": round(mape, 2)})

    component_forecasts = {name: predictor(values, horizon) for name, predictor in candidates.items()}
    if selected_name == ENSEMBLE_NAME:
        future = [
            round(sum(weights[name] * component_forecasts[name][index] for name in candidates), 1)
            for index in range(horizon)
        ]
        selected_validation = ensemble_validation
    else:
        future = [round(value, 1) for value in component_forecasts[selected_name]]
        selected_validation = evaluation_predictions[selected_name]
    calibration_residuals: list[float] = []
    for actual, predictions in zip(fold_actuals, fold_predictions, strict=True):
        if selected_name == ENSEMBLE_NAME:
            calibrated = [
                sum(weights[name] * predictions[name][index] for name in candidates)
                for index in range(len(actual))
            ]
        else:
            calibrated = predictions[selected_name]
        calibration_residuals.extend(
            abs(value - estimate) for value, estimate in zip(actual, calibrated, strict=True)
        )
    base_interval = max(1.0, _quantile(calibration_residuals, 0.90))
    horizon_intervals = [
        base_interval * (1 + 0.12 * math.sqrt((index + 1) / 7))
        for index in range(horizon)
    ]
    holdout_mae, holdout_mape = _candidate_metrics(evaluation_actual, selected_validation)
    return {
        "selected_model": selected_name,
        "validation_days": len(evaluation_actual),
        "cv_folds": fold_count,
        "mae": round(holdout_mae, 2),
        "mape": round(holdout_mape, 2),
        "engine": "xgboost" if XGBRegressor is not None else "native_gradient_boosting",
        "ensemble_weights": weights,
        "interval_method": "rolling-origin 오차 90백분위·예측거리별 완만한 확대",
        "leaderboard": selection_results,
        "forecast": future,
        "lower": [round(max(0.0, value - interval), 1) for value, interval in zip(future, horizon_intervals, strict=True)],
        "upper": [round(value + interval, 1) for value, interval in zip(future, horizon_intervals, strict=True)],
    }
