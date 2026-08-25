import re

SELECT_PATTERN=re.compile(r"^\s*select\b",re.IGNORECASE)
def require_read_only_query(query:str)->str:
    if not SELECT_PATTERN.match(query) or ";" in query.rstrip().rstrip(";"):
        raise ValueError("Only a single SELECT query is permitted")
    return query

