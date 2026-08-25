from pathlib import Path
from app.config import GENERATED_DIR

CHART_DIR=GENERATED_DIR/"charts"; CHART_DIR.mkdir(parents=True,exist_ok=True)
def chart_path(name:str)->Path: return CHART_DIR/f"{Path(name).stem}.json"

