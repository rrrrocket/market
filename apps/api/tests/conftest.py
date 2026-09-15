import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_market.db"
os.environ["LATEST_COMPLETE_TRADE_YEAR"] = "2025"
os.environ["TRADE_DATA_PROVIDER"] = "fixture"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

get_settings.cache_clear()
from app.core.database import Base, engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    Path("test_market.db").unlink(missing_ok=True)
