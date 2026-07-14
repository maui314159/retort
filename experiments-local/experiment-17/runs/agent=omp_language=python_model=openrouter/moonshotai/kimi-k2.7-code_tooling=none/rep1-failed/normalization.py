"""Text and team name normalization.

Brazilian soccer datasets use many different spellings for the same club.
This module maps raw team names to canonical display names and resolves
user queries back to those canonical names.
"""

from __future__ import annotations

import re
import unicodedata

BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Roots where the state suffix is required to tell clubs apart.
AMBIGUOUS_ROOTS = {
    "america", "américa", "atletico", "atlético", "athletico", "botafogo",
    "flamengo", "fluminense", "guarani", "internacional", "juventude",
    "nautico", "náutico", "operario", "operário", "portuguesa", "rio branco",
    "river", "santa cruz", "santos", "sao francisco", "são francisco",
    "sao jose", "são josé", "sao raimundo", "são raimundo", "vitoria",
    "vitória", "ypiranga", "y-piranga",
}


def _unaccent(text: str) -> str:
    """Drop diacritics using unicode decomposition."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalize_text(text: str) -> str:
    """Lower-case, remove accents/diacritics and collapse punctuation."""
    clean = _unaccent(str(text).strip()).lower()
    clean = re.sub(r"[^a-z0-9]+", " ", clean)
    return clean.strip()


def clean_token_key(text: str) -> str:
    """Strict token key used for exact alias lookup."""
    return re.sub(r"\s+", " ", normalize_text(text))


# Canonical display name -> raw aliases observed in the datasets.
TEAM_ALIASES: dict[str, list[str]] = {
    "América-MG": [
        "América - MG",
        "América-MG",
        "America - MG",
        "America-MG",
        "America MG",
    ],
    "Athletico Paranaense": [
        "Athletico Paranaense",
        "Athletico Paranaense - PR",
        "Athletico-PR",
        "Atlético Paranaense",
        "Atlético Paranaense - PR",
        "Atletico Paranaense",
        "Atletico - PR",
        "Atlético - PR",
        "Atletico-PR",
        "Atlético-PR",
    ],
    "Atlético Mineiro": [
        "Atlético Mineiro",
        "Atlético Mineiro - MG",
        "Atletico Mineiro",
        "Atlético-MG",
        "Atletico-MG",
        "Athletic Club MG",
    ],
    "Atlético Goianiense": [
        "Atlético Goianiense",
        "Atlético-GO",
        "Atletico-GO",
        "Atlético - GO",
        "Atletico - GO",
        "Atletico Goianiense",
    ],
    "Avaí": [
        "Avaí",
        "Avai",
        "Avaí - SC",
        "Avai-SC",
    ],
    "Bahia": [
        "Bahia",
        "Bahia - BA",
        "Bahia-BA",
        "EC Bahia",
    ],
    "Botafogo": [
        "Botafogo",
        "Botafogo - RJ",
        "Botafogo-RJ",
        "Botafogo RJ",
    ],
    "Ceará": [
        "Ceará",
        "Ceara",
        "Ceará - CE",
        "Ceara-CE",
    ],
    "Chapecoense": [
        "Chapecoense",
        "Chapecoense - SC",
        "Chapecoense-SC",
    ],
    "Corinthians": [
        "Corinthians",
        "Corinthians - SP",
        "Corinthians-SP",
        "Sport Club Corinthians Paulista",
    ],
    "Coritiba": [
        "Coritiba",
        "Coritiba - PR",
        "Coritiba PR",
        "Coritiba-PR",
    ],
    "Cruzeiro": [
        "Cruzeiro",
        "Cruzeiro - MG",
        "Cruzeiro-MG",
    ],
    "Flamengo": [
        "Flamengo",
        "Flamengo - RJ",
        "Flamengo-RJ",
    ],
    "Fluminense": [
        "Fluminense",
        "Fluminense - RJ",
        "Fluminense-RJ",
        "Fluminense RJ",
    ],
    "Fortaleza": [
        "Fortaleza",
        "Fortaleza - CE",
        "Fortaleza EC",
        "Fortaleza FC",
        "Fortaleza-CE",
    ],
    "Goiás": [
        "Goiás",
        "Goias",
        "Goiás - GO",
        "Goias-GO",
    ],
    "Grêmio": [
        "Grêmio",
        "Gremio",
        "Grêmio - RS",
        "Gremio-RS",
        "Gremio RS",
    ],
    "Internacional": [
        "Internacional",
        "Internacional - RS",
        "Internacional-RS",
        "Internacional RS",
    ],
    "Palmeiras": [
        "Palmeiras",
        "Palmeiras - SP",
        "Palmeiras-SP",
    ],
    "Santos": [
        "Santos",
        "Santos - SP",
        "Santos-SP",
    ],
    "São Paulo": [
        "São Paulo",
        "Sao Paulo",
        "São Paulo - SP",
        "Sao Paulo-SP",
    ],
    "Sport": [
        "Sport",
        "Sport Recife",
        "Sport - PE",
        "Sport-PE",
    ],
    "Vasco da Gama": [
        "Vasco",
        "Vasco da Gama",
        "Vasco da Gama - RJ",
        "Vasco da Gama-RJ",
        "Vasco Da Gama RJ",
    ],
    "Vitória": [
        "Vitória",
        "Vitoria",
        "Vitória - BA",
        "Vitoria-BA",
    ],
}

# Build exact lookup tables.
_RAW_TO_CANONICAL: dict[str, str] = {}
for _canonical_name, _aliases in TEAM_ALIASES.items():
    for _alias in [_canonical_name, *_aliases]:
        _RAW_TO_CANONICAL[clean_token_key(_alias)] = _canonical_name


def _remove_state_suffix(name: str) -> tuple[str, str | None]:
    """Return (root, state) if a trailing Brazilian-state suffix is present."""
    name = re.sub(r"\s*\([A-Za-z]+\)\s*$", "", name).strip()
    match = re.search(r"[\s\-]+([A-Z]{2})\s*$", name)
    if match and match.group(1) in BRAZIL_STATES:
        root = name[: match.start()].strip(" -")
        return root, match.group(1)
    return name, None


def normalize_team_name(raw_name: str) -> str:
    """Map a raw team name to a normalized canonical display name."""
    raw = str(raw_name).strip()
    if not raw:
        return raw

    # Exact known alias? e.g. "Flamengo-RJ" or "América - MG"
    key = clean_token_key(raw)
    if key in _RAW_TO_CANONICAL:
        return _RAW_TO_CANONICAL[key]

    root, state = _remove_state_suffix(raw)
    root_key = clean_token_key(root)

    # Preserve state for clubs whose root name is shared across states.
    if state and root_key in AMBIGUOUS_ROOTS:
        return f"{root} - {state}"

    # Maybe the state-less root is a known alias on its own.
    if root_key in _RAW_TO_CANONICAL:
        return _RAW_TO_CANONICAL[root_key]

    return root


def canonical_names() -> list[str]:
    """Return all configured canonical display names."""
    return list(TEAM_ALIASES.keys())


def resolve_team_query(query: str) -> list[str]:
    """Return canonical names that match a free-text user query.

    The query may be a full canonical name, a common alias, or a substring of
    one (e.g. "Sao Paulo" matches "São Paulo").
    """
    q = clean_token_key(query)
    if not q:
        return []

    matches: list[str] = []
    seen: set[str] = set()

    for canonical_name, aliases in TEAM_ALIASES.items():
        candidates = [canonical_name, *aliases]
        for candidate in candidates:
            candidate_key = clean_token_key(candidate)
            if q == candidate_key:
                if canonical_name not in seen:
                    matches.append(canonical_name)
                    seen.add(canonical_name)
                break
            if len(q) >= 3 and q in candidate_key:
                boundary = re.search(
                    rf"(^|[\s\-]){re.escape(q)}($|[\s\-])", candidate_key
                )
                if candidate_key == q or candidate_key.startswith(q + " ") or boundary:
                    if canonical_name not in seen:
                        matches.append(canonical_name)
                        seen.add(canonical_name)
                    break

    return matches


def parse_date(val):
    """Parse a date-ish value and return a pandas Timestamp or NaT."""
    import pandas as pd

    if val is None:
        return pd.NaT
    s = str(val).strip()
    if not s:
        return pd.NaT
    dayfirst = "/" in s and s.index("/") == 2
    try:
        return pd.to_datetime(s, dayfirst=dayfirst, errors="coerce")
    except Exception:
        return pd.NaT
