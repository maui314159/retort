import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brazilian_soccer_mcp import load_all, QueryEngine
from brazilian_soccer_mcp.mcp_server import build_server

DATA_DIR = os.environ.get("BRAZILIAN_SOCCER_DATA", str(ROOT / "data" / "kaggle"))


@pytest.fixture(scope="session")
def bundle():
    return load_all(DATA_DIR)


@pytest.fixture(scope="session")
def engine(bundle):
    return QueryEngine(bundle)


@pytest.fixture(scope="session")
def server(engine):
    return build_server(engine)
