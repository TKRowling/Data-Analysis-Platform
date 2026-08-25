import pandas as pd

def correlation_matrix(frame: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    return frame.select_dtypes("number").corr(method=method)

