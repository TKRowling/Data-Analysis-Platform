import io
import pandas as pd
def load_csv(content: bytes) -> pd.DataFrame: return pd.read_csv(io.BytesIO(content))

