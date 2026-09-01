"""Name normalization utilities.

The datasets use several naming conventions for the same team:

- with state suffix:      "Palmeiras-SP", "América - MG"
- without suffix:         "Palmeiras", "América"
- full legal names:       "Sport Club Corinthians Paulista"
- parenthetical notes:    "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"

`normalize_name` maps all of these to a canonical lowercase,
accent-free key so that lookups work regardless of the variant a
question uses. A reverse registry keeps the most human-friendly raw
variant for display purposes.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Common abbreviations / legal-name words that people rarely type.
# Note: "sport" is NOT stripped - Sport Club do Recife is named "Sport".
_STRIP_WORDS = {
    "sc", "fc", "ec", "ac", "aa", "club", "clube", "esporte",
    "sporting", "do", "da", "de", "e",
}

# Cross-dataset equivalences: variant key -> canonical key.
_ALIASES = {
    "atletico": "atletico mineiro",
    "atl mineiro": "atletico mineiro",
    "america mineiro": "america",
    "athletico": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "corinthians paulista": "corinthians",
    "vasco": "vasco gama",  # "Vasco da Gama" normalizes to "vasco gama"
    "nautico capibaribe": "nautico",
    "sport recife": "sport",
    "recife": "sport",
    "do remo": "remo",
    "ad confianca": "confianca",
    "bragantino": "red bull bragantino",
    "portuguesa desportos": "portuguesa",
    "novorizontino": "gremio novorizontino",
}

_PAREN_RE = re.compile(r"\([^)]*\)")
_STATE_SUFFIX_RE = re.compile(r"\s*-\s*[A-Z]{2}\s*$")
# Also handles "Flamengo - RJ" and "Palmeiras-SP"
_DASH_TAIL_RE = re.compile(r"[-–]\s*[A-Za-zÀ-ÿ]{2,3}\s*$")


def strip_accents(text: str) -> str:
    """Remove diacritics: 'São Paulo' -> 'Sao Paulo'."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_name(raw: str) -> str:
    """Return the canonical key for a team name."""
    if not raw:
        return ""
    name = raw.strip()
    # Drop parenthetical remarks e.g. "(antigo Esporte Clube Barreira)"
    name = _PAREN_RE.sub(" ", name)
    # Drop trailing state suffix: "-SP", " - RJ", "-RJ"
    name = _STATE_SUFFIX_RE.sub("", name.strip())
    name = name.strip()
    # Lowercase, unaccented, collapsed whitespace.
    name = strip_accents(name).lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        return ""
    tokens = [t for t in name.split(" ") if t not in _STRIP_WORDS]
    # Drop a *single* trailing bare state code left over (e.g. "america mg").
    if tokens and re.fullmatch(r"[a-z]{2}", tokens[-1]) and len(tokens) > 1:
        tokens = tokens[:-1]
    key = " ".join(tokens) if tokens else name
    return _ALIASES.get(key, key)


def normalize_player_name(raw: str) -> str:
    """Canonical key for a player name (accent-free, case-insensitive)."""
    return re.sub(r"\s+", " ", strip_accents(raw or "").lower()).strip()


class NameRegistry:
    """Maps canonical keys back to a display name.

    The display name chosen for a key is the most frequently seen raw
    variant, which keeps e.g. "Flamengo" (not "flamengo-rj") in output.
    """

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._raw: dict[str, str] = {}

    def register(self, raw: str) -> None:
        key = normalize_name(raw)
        if not key:
            return
        self._counts[key] += 1
        current = self._raw.get(key)
        if current is None:
            self._raw[key] = raw.strip()
        else:
            # Prefer shorter, then more-frequent variants: avoids
            # "Boavista Sport Club (antigo ...) - RJ" style monsters.
            if len(raw) < len(current) or self._counts[key] % 50 == 0:
                self._raw[key] = raw.strip()

    def display(self, key: str) -> str:
        return self._raw.get(key, key)

    def count(self, key: str) -> int:
        """How often this canonical key was seen (popularity)."""
        return self._counts.get(key, 0)

    def keys(self) -> list[str]:
        return sorted(self._counts)
