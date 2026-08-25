import pandas as pd

def standardize(series: pd.Series) -> pd.Series:
    deviation=series.std()
    return (series-series.mean())/deviation if deviation else series*0

def min_max_scale(series: pd.Series) -> pd.Series:
    span=series.max()-series.min()
    return (series-series.min())/span if span else series*0

