import pandas as pd

def duplicate_summary(frame: pd.DataFrame) -> dict:
    count = int(frame.duplicated().sum())
    return {"count": count, "percent": round(count / max(len(frame), 1) * 100, 2)}

