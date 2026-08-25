import pandas as pd

def aggregate(frame: pd.DataFrame, metric: str, operation: str, group_by: str | None = None) -> pd.DataFrame:
    if operation not in {"sum", "mean", "median", "min", "max", "count"}: raise ValueError("Unsupported aggregation")
    if group_by: return frame.groupby(group_by, dropna=False)[metric].agg(operation).reset_index()
    return pd.DataFrame({"metric": [metric], "operation": [operation], "value": [getattr(frame[metric], operation)()]})

