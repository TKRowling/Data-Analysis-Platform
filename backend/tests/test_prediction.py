import numpy as np
import pandas as pd
import pytest

from app.tools.prediction.classification import majority_baseline, train_classifier
from app.tools.prediction.forecasting import naive_forecast, trend_forecast
from app.tools.prediction.regression import train_regression


def test_regression_recovers_a_known_relationship():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 1, 200)
    frame = pd.DataFrame({"x": x, "y": 3 * x + 5 + rng.normal(0, 0.05, 200)})
    result = train_regression(frame, ["x"], "y")
    assert result["r2"] > 0.98
    assert result["coefficients"]["x"] == pytest.approx(3, abs=0.1)
    assert result["intercept"] == pytest.approx(5, abs=0.1)
    assert result["rmse"] >= 0
    assert result["train_rows"] + result["test_rows"] == result["rows"]


def test_regression_reports_a_weak_model_honestly():
    rng = np.random.default_rng(5)
    frame = pd.DataFrame({"x": rng.normal(0, 1, 200), "y": rng.normal(0, 1, 200)})
    assert train_regression(frame, ["x"], "y")["r2"] < 0.2


def test_regression_needs_enough_rows():
    frame = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
    with pytest.raises(ValueError, match="at least 20"):
        train_regression(frame, ["x"], "y")


def test_regression_rejects_unknown_columns(rich_record):
    with pytest.raises(ValueError, match="Unknown columns"):
        train_regression(rich_record.frame, ["nope"], "revenue")


def test_classifier_beats_baseline_on_separable_data():
    rng = np.random.default_rng(7)
    signal = np.concatenate([rng.normal(-3, 0.5, 100), rng.normal(3, 0.5, 100)])
    frame = pd.DataFrame({"signal": signal, "label": ["low"] * 100 + ["high"] * 100})
    result = train_classifier(frame, ["signal"], "label")
    assert result["accuracy"] > 0.9
    assert result["beats_baseline"] is True
    assert 0 <= result["precision"] <= 1 and 0 <= result["recall"] <= 1
    assert result["strongest_feature"] == "signal"


def test_classifier_reports_noise_as_no_signal():
    rng = np.random.default_rng(9)
    frame = pd.DataFrame({"noise": rng.normal(0, 1, 200),
                          "label": rng.choice(["a", "b"], 200)})
    result = train_classifier(frame, ["noise"], "label")
    assert result["accuracy"] <= result["baseline_accuracy"] + 0.2


def test_classifier_rejects_single_class():
    frame = pd.DataFrame({"x": range(40), "label": ["only"] * 40})
    with pytest.raises(ValueError, match="only one distinct value"):
        train_classifier(frame, ["x"], "label")


def test_classifier_rejects_too_many_classes():
    frame = pd.DataFrame({"x": range(60), "label": [f"class_{i}" for i in range(60)]})
    with pytest.raises(ValueError, match="too many"):
        train_classifier(frame, ["x"], "label")


def test_majority_baseline():
    frame = pd.DataFrame({"label": ["a", "a", "a", "b"]})
    result = majority_baseline(frame, "label")
    assert result["predicted_class"] == "a"
    assert result["accuracy"] == pytest.approx(0.75)


def test_trend_forecast_extrapolates_a_line():
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    result = trend_forecast(series, periods=2)
    assert result["direction"] == "increasing"
    assert result["fit_r2"] == pytest.approx(1.0)
    assert result["forecast"][0] == pytest.approx(60.0)
    assert result["forecast"][1] == pytest.approx(70.0)
    assert len(result["labels"]) == 2


def test_trend_forecast_uses_datetime_spacing():
    index = pd.date_range("2024-01-01", periods=6, freq="D")
    result = trend_forecast(pd.Series([1.0, 2, 3, 4, 5, 6], index=index), periods=1)
    assert result["labels"] == ["2024-01-07"]


def test_trend_forecast_needs_enough_points():
    with pytest.raises(ValueError, match="at least 4"):
        trend_forecast(pd.Series([1.0, 2.0]), periods=1)


def test_naive_forecast_still_available():
    assert naive_forecast(pd.Series([1.0, 2.0, 7.0]), periods=2)["forecast"] == [7.0, 7.0]
