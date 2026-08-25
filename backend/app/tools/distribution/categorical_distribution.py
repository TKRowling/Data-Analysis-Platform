import pandas as pd

def categorical_distribution(series: pd.Series, limit: int = 30) -> list[dict]:
    counts=series.fillna("(missing)").astype(str).value_counts().head(limit)
    return [{"value":name,"count":int(count),"proportion":round(count/max(len(series),1),4)} for name,count in counts.items()]

