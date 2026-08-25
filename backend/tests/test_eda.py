import numpy as np
import pandas as pd
import pytest

from app.core.exceptions import AnalysisError
from app.services.dataset_service import store
from app.services.eda_service import correlation, distribution, overview, quality, statistics


def test_overview_profiles_columns(sample_record):
    result = overview(sample_record)
    assert result["rows"] == 4 and result["columns_count"] == 3
    assert result["kinds"]["numeric"] == 2
    assert result["kinds"]["categorical"] == 1


def test_overview_classifies_booleans_separately():
    record = store.add("flags.csv", "test", pd.DataFrame({"active": [True, False, True], "score": [1, 2, 3]}))
    kinds = overview(record)["kinds"]
    assert kinds["boolean"] == 1 and kinds["numeric"] == 1


def test_statistics_covers_numeric_categorical_and_histograms(rich_record):
    result = statistics(rich_record)
    assert {s["column"] for s in result["numeric"]} >= {"units", "price", "revenue"}
    assert {c["column"] for c in result["categorical"]} >= {"region", "product", "grade"}
    assert len(result["histograms"]) == len(result["numeric"])
    assert all("missing" in c for c in result["categorical"])


def test_quality_detects_duplicates_and_outliers(sample_record):
    result = quality(sample_record)
    assert result["duplicate_rows"] == 0
    revenue = next(o for o in result["outliers"] if o["column"] == "revenue")
    assert revenue["count"] == 1
    assert 0 <= result["score"] <= 100


def test_quality_flags_numeric_stored_as_text():
    record = store.add("typed.csv", "test", pd.DataFrame({
        "amount": ["1", "2", "3", "4", "5"],
        "real": [1.0, 2.0, 3.0, 4.0, 5.0],
    }))
    issues = {i["issue"] for i in quality(record)["datatype_issues"]}
    assert "numeric_stored_as_text" in issues


def test_quality_flags_mixed_types():
    record = store.add("mixed.csv", "test", pd.DataFrame({"value": [1, "two", 3.0, None, "five"]}))
    issues = {i["issue"] for i in quality(record)["datatype_issues"]}
    assert "mixed_types" in issues


def test_quality_survives_an_all_null_column():
    record = store.add("empty.csv", "test", pd.DataFrame({"blank": [None, None], "n": [1, 2]}))
    result = quality(record)
    assert any(i["issue"] == "empty_column" for i in result["datatype_issues"])
    assert 0 <= result["score"] <= 100


def test_correlation_finds_strong_pairs(rich_record):
    result = correlation(rich_record)
    assert "units" in result["columns"]
    assert all(abs(pair["value"]) >= 0.7 for pair in result["strong"])
    assert all(pair["direction"] in {"positive", "negative"} for pair in result["strong"])


def test_correlation_rejects_unknown_method(sample_record):
    with pytest.raises(AnalysisError):
        correlation(sample_record, method="voodoo")


def test_numeric_distribution_has_box_and_interpretation(rich_record):
    result = distribution(rich_record, "revenue")
    assert result["kind"] == "numeric"
    assert set(result["box"]) == {"min", "q1", "median", "q3", "max"}
    assert result["box"]["q1"] <= result["box"]["median"] <= result["box"]["q3"]
    assert result["interpretation"]


def test_categorical_distribution_has_proportions(rich_record):
    result = distribution(rich_record, "region")
    assert result["kind"] == "categorical"
    assert sum(entry["proportion"] for entry in result["values"]) == pytest.approx(1.0, abs=0.02)
    assert all("label" in entry for entry in result["values"])
    assert result["interpretation"]


def test_distribution_rejects_unknown_column(sample_record):
    with pytest.raises(AnalysisError):
        distribution(sample_record, "not_a_column")


def test_json_is_serializable_with_infinities():
    """NaN and inf must never reach the client as invalid JSON."""
    import json
    record = store.add("wild.csv", "test", pd.DataFrame({
        "x": [1.0, np.inf, -np.inf, np.nan, 5.0], "y": [1.0, 2.0, 3.0, 4.0, 5.0]}))
    for payload in (overview(record), statistics(record), quality(record), correlation(record)):
        json.dumps(payload, allow_nan=False)
