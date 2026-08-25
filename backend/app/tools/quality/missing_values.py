import pandas as pd

def missing_summary(frame: pd.DataFrame) -> list[dict]:
    return [{"column": c, "count": int(frame[c].isna().sum()), "percent": round(frame[c].isna().mean()*100, 2)} for c in frame if frame[c].isna().any()]

