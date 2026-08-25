import io
import pandas as pd
def load_excel(content: bytes) -> pd.DataFrame: return pd.read_excel(io.BytesIO(content))

