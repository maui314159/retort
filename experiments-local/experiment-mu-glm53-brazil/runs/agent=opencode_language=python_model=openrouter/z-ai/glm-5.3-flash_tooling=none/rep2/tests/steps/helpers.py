"""Shared state helpers for BDD step definitions."""

from __future__ import annotations

from typing import Any


class World:
    """Carries query results between Given/When/Then steps."""

    def __init__(self, engine) -> None:
        self.engine = engine
        self.result: dict[str, Any] = {}
        self.params: dict[str, Any] = {}
