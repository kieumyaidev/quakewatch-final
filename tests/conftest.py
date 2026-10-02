import pytest
from sqlalchemy import create_engine

from quakewatch.db import migrate


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    migrate(engine)
    return engine
