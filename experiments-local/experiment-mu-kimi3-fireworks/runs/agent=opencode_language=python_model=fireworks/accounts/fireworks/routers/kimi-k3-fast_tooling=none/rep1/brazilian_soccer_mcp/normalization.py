"""Text, team-name and date normalization helpers.

Why: the six Kaggle datasets use different team-naming conventions
("Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista",
"América - MG", ...) and several date formats (ISO, ISO+time,
DD/MM/YYYY).  All matching in the query layer is done on the
*canonical keys* produced here so that every convention resolves to
the same team.

What:
    - ``strip_accents`` / ``normalize_text``  -- UTF-8, accent and case folding
    - ``parse_team``                          -- raw name -> (base, state) parts
    - ``team_key``                            -- raw name -> canonical match key
    - ``TeamRegistry``                        -- key <-> display-name mapping + fuzzy resolution
    - ``parse_date`` / ``parse_date_series``  -- multi-format date parsing
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------


def strip_accents(text: str) -> str:
    """Remove diacritics: "São Paulo" -> "Sao Paulo", "Grêmio" -> "Gremio"."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    """Accent-folded, lowercased, whitespace-collapsed version of *text*."""
    text = strip_accents(str(text).strip())
    text = re.sub(r"[_.]+", " ", text)  # "A.b.c." -> "a b c"
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


# ---------------------------------------------------------------------------
# Team-name parsing
# ---------------------------------------------------------------------------

# Trailing state / country suffixes: "-SP", " - MG", "(URU)", "-EQU", " RJ".
_STATE_PAREN_RE = re.compile(r"\s*\(([A-Z]{2,3})\)\s*$")
_STATE_DASH_RE = re.compile(r"\s*[-–]\s*([A-Z]{2,3})\s*$")
_STATE_SPACE_RE = re.compile(r"\s+([A-Za-z]{2,3})\s*$")

# Tokens allowed as trailing state/country codes (prevents stripping club
# suffixes like "EC"/"FC" from "4 de Julho EC").
_BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}
_COUNTRY_CODES = {
    "URU", "ARG", "CHI", "COL", "PER", "BOL", "PAR", "VEN", "ECU", "EQU",
    "MEX", "USA",
}
_STATE_TOKENS = _BRAZIL_STATES | _COUNTRY_CODES

# Club-designator tokens stripped from the end of a base name so that
# "4 de Julho EC" and "4 de Julho - PI" can still resolve together.
_CLUB_SUFFIX_RE = re.compile(r"\s+(ec|fc|cf|ac|sc)$")

# Aliases map a normalized (accent-free, lowercased, state-stripped) name to a
# canonical (base, state) pair.  ``None`` state means "no implied state".
_ALIASES: dict[str, tuple[str, str | None]] = {
    # Corinthians
    "sport club corinthians paulista": ("corinthians", "sp"),
    "sc corinthians paulista": ("corinthians", "sp"),
    "corinthians": ("corinthians", "sp"),
    # São Paulo
    "sao paulo": ("sao paulo", "sp"),
    "sao paulo fc": ("sao paulo", "sp"),
    # Palmeiras
    "palmeiras": ("palmeiras", "sp"),
    "se palmeiras": ("palmeiras", "sp"),
    # Santos
    "santos": ("santos", "sp"),
    "santos fc": ("santos", "sp"),
    # Flamengo / Fluminense / Vasco / Botafogo (RJ)
    "flamengo": ("flamengo", "rj"),
    "cr flamengo": ("flamengo", "rj"),
    "fluminense": ("fluminense", "rj"),
    "fluminense fc": ("fluminense", "rj"),
    "vasco": ("vasco", "rj"),
    "vasco da gama": ("vasco", "rj"),
    "cr vasco da gama": ("vasco", "rj"),
    "botafogo": ("botafogo", "rj"),
    "botafogo fr": ("botafogo", "rj"),
    "botafogo de futebol e regatas": ("botafogo", "rj"),
    # Atlético variants (state disambiguates!)
    "atletico mineiro": ("atletico", "mg"),
    "clube atletico mineiro": ("atletico", "mg"),
    "atletico paranaense": ("atletico", "pr"),
    "athletico paranaense": ("atletico", "pr"),
    "athletico": ("atletico", "pr"),
    "ca paranaense": ("atletico", "pr"),
    "atletico goianiense": ("atletico", "go"),
    # América variants
    "america mineiro": ("america", "mg"),
    "america fc minas gerais": ("america", "mg"),
    "america de natal": ("america", "rn"),
    # Grêmio / Internacional / Juventude (RS)
    "gremio": ("gremio", "rs"),
    "gremio fbpa": ("gremio", "rs"),
    "internacional": ("internacional", "rs"),
    "sc internacional": ("internacional", "rs"),
    "juventude": ("juventude", "rs"),
    "ec juventude": ("juventude", "rs"),
    "brasil de pelotas": ("brasil de pelotas", "rs"),
    # Cruzeiro / Bahia / Vitória / Ceará / Fortaleza / Sport ...
    "cruzeiro": ("cruzeiro", "mg"),
    "cruzeiro ec": ("cruzeiro", "mg"),
    "bahia": ("bahia", "ba"),
    "ec bahia": ("bahia", "ba"),
    "vitoria": ("vitoria", "ba"),
    "ec vitoria": ("vitoria", "ba"),
    "ceara": ("ceara", "ce"),
    "ceara sporting club": ("ceara", "ce"),
    "ceara sc": ("ceara", "ce"),
    "fortaleza": ("fortaleza", "ce"),
    "fortaleza ec": ("fortaleza", "ce"),
    "fortaleza fc": ("fortaleza", "ce"),
    "fortaleza esporte clube": ("fortaleza", "ce"),
    "sport": ("sport", "pe"),
    "sport recife": ("sport", "pe"),
    "sport club do recife": ("sport", "pe"),
    "sport club recife": ("sport", "pe"),
    "nautico": ("nautico", "pe"),
    "santa cruz": ("santa cruz", "pe"),
    "santa cruz fc": ("santa cruz", "pe"),
    "joinville": ("joinville", "sc"),
    "joinville ec": ("joinville", "sc"),
    # Other Série A regulars
    "coritiba": ("coritiba", "pr"),
    "coritiba foot ball club": ("coritiba", "pr"),
    "parana": ("parana", "pr"),
    "parana clube": ("parana", "pr"),
    "figueirense": ("figueirense", "sc"),
    "figueirense fc": ("figueirense", "sc"),
    "avai": ("avai", "sc"),
    "avai fc": ("avai", "sc"),
    "chapecoense": ("chapecoense", "sc"),
    "criciuma": ("criciuma", "sc"),
    "criciuma ec": ("criciuma", "sc"),
    "goias": ("goias", "go"),
    "goias ec": ("goias", "go"),
    "ponte preta": ("ponte preta", "sp"),
    "guarani": ("guarani", "sp"),
    "guarani fc": ("guarani", "sp"),
    "portuguesa": ("portuguesa", "sp"),
    "bragantino": ("bragantino", "sp"),
    "red bull bragantino": ("bragantino", "sp"),
    "rb bragantino": ("bragantino", "sp"),
    "csa": ("csa", "al"),
    "cuiaba": ("cuiaba", "mt"),
    "sao caetano": ("sao caetano", "sp"),
    "barueri": ("barueri", "sp"),
    "brasiliense": ("brasiliense", "df"),
    "paysandu": ("paysandu", "pa"),
    "remo": ("remo", "pa"),
    "abc": ("abc", "rn"),
    "america fc natal": ("america", "rn"),
    "america rn": ("america", "rn"),
}


def parse_team(raw_name: object) -> tuple[str, str | None]:
    """Split a raw team name into (base, state) canonical parts.

    Handles state/country suffixes ("Flamengo-RJ", "América - MG",
    "Nacional (URU)"), full club names ("Sport Club Corinthians
    Paulista") and accent/case variations.
    """
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ("", None)
    text = str(raw_name).strip().strip('"')
    state: str | None = None

    m = _STATE_PAREN_RE.search(text)
    if m:
        state = m.group(1).lower()
        text = text[: m.start()]
    else:
        m = _STATE_DASH_RE.search(text)
        if m:
            state = m.group(1).lower()
            text = text[: m.start()]
        else:
            m = _STATE_SPACE_RE.search(text)
            if m and m.group(1).upper() in _STATE_TOKENS:
                state = m.group(1).lower()
                text = text[: m.start()]

    base = normalize_text(text)
    base = re.sub(r"[^\w\s-]", " ", base)  # drop leftover punctuation
    base = re.sub(r"\s+", " ", base).strip(" -")

    alias = _ALIASES.get(base)
    if alias is not None:
        abase, astate = alias
        return (abase, state or astate)
    # No alias: strip trailing club designators ("Fortaleza FC" -> "fortaleza")
    # and retry, so suffixed spellings still merge with the canonical entry.
    stripped = _CLUB_SUFFIX_RE.sub("", base)
    if stripped != base:
        alias = _ALIASES.get(stripped)
        if alias is not None:
            abase, astate = alias
            return (abase, state or astate)
        return (stripped, state)
    return (base, state)


def team_key(raw_name: object) -> str:
    """Canonical match key for a raw team name.

    "Palmeiras-SP" -> "palmeiras sp"; "Palmeiras" -> "palmeiras sp"
    (via alias); "Boca Juniors" -> "boca juniors" (no state known).
    """
    base, state = parse_team(raw_name)
    if not base:
        return ""
    return f"{base} {state}" if state else base


def team_base(raw_name: object) -> str:
    """State-less base of a team name ("América-MG" -> "america")."""
    return parse_team(raw_name)[0]


# ---------------------------------------------------------------------------
# Team registry: canonical key <-> pretty display name, fuzzy resolution
# ---------------------------------------------------------------------------


class TeamRegistry:
    """Maps canonical keys to the most common display form of the name."""

    def __init__(self) -> None:
        self._display: dict[str, tuple[str, int]] = {}  # key -> (display, count)
        self._bases: dict[str, set[str]] = {}  # base -> keys

    def register(self, raw_name: object) -> str:
        base, state = parse_team(raw_name)
        key = f"{base} {state}" if state else base
        return self.register_key(raw_name, key, base)

    def register_key(self, raw_name: object, key: str, base: str | None = None) -> str:
        """Register *raw_name* under an explicit canonical *key*."""
        if not key:
            return key
        if base is None:
            base = parse_team(raw_name)[0]
        display = str(raw_name).strip().strip('"')
        display = re.sub(r"\s+", " ", display)
        prev = self._display.get(key)
        if prev is None or len(display) < len(prev[0]):
            # Prefer the shortest seen form ("Flamengo" over "Flamengo-RJ").
            self._display[key] = (display, prev[1] + 1 if prev else 1)
        else:
            self._display[key] = (prev[0], prev[1] + 1)
        self._bases.setdefault(base, set()).add(key)
        return key

    def display_name(self, key: str) -> str:
        entry = self._display.get(key)
        if entry:
            return entry[0]
        # Fallback: title-case the key without its state suffix.
        parts = key.split()
        if parts and re.fullmatch(r"[a-z]{2,3}", parts[-1]):
            parts = parts[:-1]
        return " ".join(parts).title() if parts else key

    def resolve(self, name: str) -> list[str]:
        """Resolve a user-supplied team name to canonical keys.

        Order: exact key match, exact base match, alias hit, substring
        match on known bases/keys.  Returns [] when nothing matches.
        """
        if not name:
            return []
        base, state = parse_team(name)
        key = f"{base} {state}" if state else base
        if key in self._display:
            return [key]
        if base in self._bases:
            return sorted(self._bases[base])
        # Substring over keys, e.g. "corinthian" -> "corinthians sp".
        hits = [k for k in self._display if base and base in k]
        if hits:
            return sorted(hits)
        hits = [k for b, keys in self._bases.items() if base and base in b for k in keys]
        return sorted(set(hits))

    def keys(self) -> list[str]:
        return sorted(self._display)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_date(value: object) -> datetime | None:
    """Parse ISO, ISO+time and Brazilian DD/MM/YYYY date strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(value).to_pydatetime()
    text = str(value).strip().strip('"')
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(text, dayfirst="/" in text, errors="coerce")
        return None if pd.isna(ts) else ts.to_pydatetime()
    except (ValueError, TypeError):
        return None


def parse_date_series(series: pd.Series, *, dayfirst: bool = False) -> pd.Series:
    """Vectorized date parsing for a whole column."""
    return pd.to_datetime(series, format="mixed", dayfirst=dayfirst, errors="coerce")
