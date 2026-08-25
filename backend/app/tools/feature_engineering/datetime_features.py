import pandas as pd

def datetime_parts(series: pd.Series) -> pd.DataFrame:
    values=pd.to_datetime(series,errors="coerce")
    return pd.DataFrame({"year":values.dt.year,"month":values.dt.month,"day":values.dt.day,"weekday":values.dt.day_name()})

