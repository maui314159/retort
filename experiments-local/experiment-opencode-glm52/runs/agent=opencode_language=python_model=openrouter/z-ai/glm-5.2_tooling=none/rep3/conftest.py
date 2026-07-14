"""Test fixtures shared across the test suite."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import main as main_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_books.db"
    monkeypatch.setattr(main_module, "DB_PATH", str(db_file))
    app = main_module.create_app(str(db_file))
    with TestClient(app) as c:
        yield c
