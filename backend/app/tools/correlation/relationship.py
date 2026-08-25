import pandas as pd

def pair_relationship(frame: pd.DataFrame, left: str, right: str, method: str = "pearson") -> dict:
    value=float(frame[left].corr(frame[right], method=method))
    return {"left":left,"right":right,"correlation":value,"strength":"strong" if abs(value)>=.7 else "moderate" if abs(value)>=.4 else "weak"}

