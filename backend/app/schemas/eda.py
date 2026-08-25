from typing import Any
from pydantic import BaseModel

class EDAResponse(BaseModel):
    data: dict[str, Any]

