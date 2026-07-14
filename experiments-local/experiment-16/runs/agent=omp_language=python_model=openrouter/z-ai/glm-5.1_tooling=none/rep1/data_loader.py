"""Data loading, normalization, and query functions for Brazilian soccer MCP server."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# ── Team name normalization ──────────────────────────────────────────

# Known alias map: lowercase canonical → canonical display form.
# Built from the intersection of names across all datasets plus common variants.
TEAM_ALIASES: dict[str, str] = {
    # Major clubs
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "vasco da gama": "Vasco da Gama",
    "botafogo": "Botafogo",
    "corinthians": "Corinthians",
    "palmeiras": "Palmeiras",
    "sao paulo": "São Paulo",
    "são paulo": "São Paulo",
    "santos": "Santos",
    "coritiba": "Coritiba",
    "gremio": "Grêmio",
    "grêmio": "Grêmio",
    "internacional": "Internacional",
    "cruzeiro": "Cruzeiro",
    "atletico mineiro": "Atlético Mineiro",
    "atlético mineiro": "Atlético Mineiro",
    "atletico-mg": "Atlético Mineiro",
    "atlético-mg": "Atlético Mineiro",
    "bahia": "Bah