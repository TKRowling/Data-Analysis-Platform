import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

MIN_ROWS = 20
MAX_CLASSES = 20


def majority_baseline(frame: pd.DataFrame, target: str) -> dict:
    """The floor any real model must beat."""
    values = frame[target].dropna()
    if values.empty:
        raise ValueError(f"{target} has no values")
    majority = values.mode().iloc[0]
    return {"model": "majority_baseline", "predicted_class": str(majority),
            "accuracy": float((values == majority).mean()), "rows": int(len(values))}


def train_classifier(frame: pd.DataFrame, features: list[str], target: str) -> dict:
    """Fit a logistic regression and score it against the majority-class baseline."""
    if not features:
        raise ValueError("Classification needs at least one feature column")
    missing = [c for c in features + [target] if c not in frame.columns]
    if missing:
        raise ValueError(f"Unknown columns: {', '.join(missing)}")

    clean = frame[features + [target]].dropna()
    clean = clean[clean[features].apply(lambda col: pd.to_numeric(col, errors="coerce")).notna().all(axis=1)]
    if len(clean) < MIN_ROWS:
        raise ValueError(f"Classification needs at least {MIN_ROWS} complete rows; found {len(clean)}")

    labels = clean[target].astype(str)
    class_count = labels.nunique()
    if class_count < 2:
        raise ValueError(f"{target} has only one distinct value — there is nothing to classify")
    if class_count > MAX_CLASSES:
        raise ValueError(f"{target} has {class_count} distinct values, too many to classify (limit {MAX_CLASSES})")
    if labels.value_counts().min() < 2:
        raise ValueError(f"Every class in {target} needs at least 2 rows to split into train and test")

    x = clean[features].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    x_train, x_test, y_train, y_test = train_test_split(x, labels, test_size=0.25, random_state=42, stratify=labels)
    scaler = StandardScaler().fit(x_train)
    model = LogisticRegression(max_iter=1000).fit(scaler.transform(x_train), y_train)
    predictions = model.predict(scaler.transform(x_test))

    precision, recall, f1, _ = precision_recall_fscore_support(y_test, predictions, average="weighted", zero_division=0)
    weights = np.abs(model.coef_).mean(axis=0)
    importance = {name: float(value) for name, value in zip(features, weights)}
    baseline = majority_baseline(clean, target)
    accuracy = float(accuracy_score(y_test, predictions))
    return {
        "model": "logistic_regression",
        "target": target,
        "features": features,
        "classes": sorted(labels.unique().tolist()),
        "rows": int(len(clean)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "accuracy": accuracy,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "feature_importance": importance,
        "strongest_feature": max(importance, key=importance.get) if importance else None,
        "baseline_accuracy": baseline["accuracy"],
        "beats_baseline": accuracy > baseline["accuracy"],
    }
