import numpy as np
import pandas as pd
import pytest

from app.services.dataset_service import store


@pytest.fixture
def sample_record():
    return store.add("sample.csv", "test", pd.DataFrame({
        "region": ["North", "South", "North", "West"],
        "revenue": [100.0, 200.0, 150.0, 1000.0],
        "units": [1, 2, 2, 5],
    }))


@pytest.fixture
def rich_record():
    """A dataset large enough for train/test splits and trend fitting."""
    rng = np.random.default_rng(11)
    rows = 120
    units = rng.integers(1, 30, rows)
    price = np.round(rng.normal(20, 4, rows).clip(2), 2)
    frame = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=rows, freq="D"),
        "region": rng.choice(["North", "South", "East"], rows),
        "product": rng.choice(["Alpha", "Beta", "Gamma", "Delta"], rows),
        "units": units,
        "price": price,
        "revenue": np.round(units * price, 2),
        "grade": rng.choice(["pass", "fail"], rows, p=[0.65, 0.35]),
    })
    return store.add("rich.csv", "test", frame)


class ScriptedClient:
    """Stands in for LLMClient. Replays queued replies, or raises to simulate an outage."""

    def __init__(self, *replies, fail=False):
        self.replies = list(replies)
        self.fail = fail
        self.calls = []

    def complete(self, prompt, system=None):
        self.calls.append(prompt)
        if self.fail:
            raise RuntimeError("Could not connect to Ollama")
        return self.replies.pop(0) if self.replies else "{}"

    def health(self):
        return not self.fail


@pytest.fixture
def scripted_client():
    return ScriptedClient
