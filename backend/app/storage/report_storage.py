from pathlib import Path
from app.config import GENERATED_DIR

REPORT_DIR=GENERATED_DIR/"reports"; REPORT_DIR.mkdir(parents=True,exist_ok=True)
def report_path(name:str)->Path: return REPORT_DIR/Path(name).name

