import pandas as pd
from sqlalchemy import Connection, text
def load_query(connection: Connection, query: str) -> pd.DataFrame: return pd.read_sql(text(query),connection)

