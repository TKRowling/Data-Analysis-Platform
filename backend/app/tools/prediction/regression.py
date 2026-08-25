import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

MIN_ROWS = 20


def train_regression(frame: pd.DataFrame, features: list[str], target: str) -> dict:
    """Fit a linear model and score it on a held-out test split."""
    if not features:
        raise ValueError("Regression needs at least one feature column")
    missing = [c for c in features + [target] if c not in frame.columns]
    if missing:
        raise ValueError(f"Unknown columns: {', '.join(missing)}")
    clean = frame[features + [target]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(clean) < MIN_ROWS:
        raise ValueError(f"Regression needs at least {MIN_ROWS} complete numeric rows; found {len(clean)}")

    x, y = clean[features].to_numpy(float), clean[target].to_numpy(float)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42)
    model = LinearRegression().fit(x_train, y_train)
    predictions = model.predict(x_test)

    coefficients = {name: float(value) for name, value in zip(features, model.coef_)}
    strongest = max(coefficients, key=lambda k: abs(coefficients[k])) if coefficients else None
    return {
        "model": "linear_regression",
        "target": target,
        "features": features,
        "rows": int(len(clean)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "intercept": float(model.intercept_),
        "coefficients": coefficients,
        "strongest_feature": strongest,
        "r2": float(r2_score(y_test, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "mae": float(mean_absolute_error(y_test, predictions)),
    }
