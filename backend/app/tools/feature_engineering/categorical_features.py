import pandas as pd

def frequency_encode(series: pd.Series) -> pd.Series:
    return series.map(series.value_counts(normalize=True))

def one_hot_encode(series: pd.Series, prefix: str | None = None) -> pd.DataFrame:
    return pd.get_dummies(series, prefix=prefix or series.name, dtype=int)

