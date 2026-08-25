from pathlib import Path

def safe_filename(filename:str)->str:
    return Path(filename).name.replace(" ","_")

