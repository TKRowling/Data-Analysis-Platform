from contextlib import contextmanager
from sqlalchemy import Engine

@contextmanager
def connection_scope(engine: Engine):
    with engine.connect() as connection: yield connection

