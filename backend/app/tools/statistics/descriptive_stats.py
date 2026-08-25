import pandas as pd

def describe_numeric(frame: pd.DataFrame) -> list[dict]:
    return frame.describe(include="number").transpose().reset_index(names="column").to_dict("records")

