"""FastAPI dependency providers."""
from typing import Annotated

from fastapi import Depends

from app.services.dataset_service import DatasetRecord, store


def get_dataset(dataset_id: str) -> DatasetRecord:
    """Resolve the active dataset for route dependency injection.

    Raises DatasetNotFoundError, which app.main maps to a 404.
    """
    return store.get(dataset_id)


ActiveDataset = Annotated[DatasetRecord, Depends(get_dataset)]
