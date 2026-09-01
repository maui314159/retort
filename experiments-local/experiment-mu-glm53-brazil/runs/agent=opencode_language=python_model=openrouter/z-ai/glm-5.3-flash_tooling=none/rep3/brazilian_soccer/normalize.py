"""Team-name normalization, alias resolution, and date parsing.

This module is the data-quality backbone of the server:

- **Team identity**: raw team names come in many shapes ("Palmeiras-SP",
  "Palmeiras - SP", "São Paulo", "Sao Paulo", "Athletico Paranaense",
  "Nacional (URU)").  ``parse_team_name`` splits a raw name into a
  ``(base, code)`` pair where *code* is an optional Brazilian state
  abbreviation (``SP``) or a country code from Copa Libertadores data
  (``URU``).  ``TeamRegistry`` then assigns each club one stable canonical
  key and one display name so the same club always matches across all six
  datasets.

- **Ambiguity rule**: if a base name maps to more than one Brazilian state
  (e.g. "Botafogo" -> RJ/PB/SP, "América" -> MG/RN), the state becomes part
  of the club identity; a bare name ("Botafogo") resolves through
  ``DEFAULT_STATE`` to the most famous club.  Country codes (URU, PAR, ...)
  are *always* kept as part of the identity because they denote different
  real clubs ("River Plate" ARG vs "River Plate-URU").

- **Text keys**: ``canonical_key`` strips accents, punctuation and generic
  club-type tokens (FC/EC/SC/AC/CF) so "A.b.c. - RN", "ABC - RN" and
  "Abc - RN" collapse to one club.

- **Dates**: ``parse_date`` accepts ISO ("2023-09-24"), ISO with time
  ("2012-05-19 18:30:00") and Brazilian ("29/03/2003") formats.

All matching is accent/case-insensitive; UTF-8 display names are preserved.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

BR_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Country suffixes seen in the Libertadores dataset.
COUNTRY_CODES = {
    "ARG", "BOL", "CHI", "COL", "EQU", "MEX", "PAR", "PER", "URU", "VEN",
}

CODES = BR_STATES | COUNTRY_CODES

_CLUB_TOKENS = {"fc", "ec", "sc", "ac", "cf", "ca"}

# Curated corrections applied to the canonical base key (accents, spaces and
# punctuation removed).  Value: (corrected_base, forced_code or None).
ALIASES: dict[str, tuple[str, str | None]] = {
    # América (RN / Natal variants)
    "americafcnatal": ("america", "RN"),
    "americadenatal": ("america", "RN"),
    # Atlético family
    "atleticomineiro": ("atletico", "MG"),
    "atleticogoianiense": ("atletico", "GO"),
    "athleticoparanaense": ("atletico", "PR"),
    "atleticoparanaense": ("atletico", "PR"),
    "athletico": ("atletico", "PR"),
    # Vasco
    "vascodagama": ("vasco", "RJ"),
    # Sport
    "sportclubdorecife": ("sport", "PE"),
    "sportrecife": ("sport", "PE"),
    # Ceará
    "cearasportingclub": ("ceara", None),
    # Brasil de Pelotas
    "brasildepelotas": ("brasil", "RS"),
    # São José (Porto Alegre) - "POA" is not a state code
    "saojosepoa": ("saojose", "RS"),
    # Desportiva Ferroviária
    "desportivaferroviaria": ("desportiva", "ES"),
    # SER Caxias == Caxias (RS)
    "sercaxias": ("caxias", None),
    # CSA long form
    "csalagoano": ("csa", None),
    # Operário Ferroviário (PR)
    "operarioferroviarioesportec": ("operario", "PR"),
    # Boavista (Saquarema, RJ)
    "boavistascsaquarema": ("boavista", "RJ"),
    "boavistasportclub": ("boavista", "RJ"),
    # Ríver is always the Piauí club ("AC" suffix is not Acre here)
    "river": ("river", "PI"),
    # Águia de Marabá
    "aguiademaraba": ("aguia", "PA"),
    # 4 de Julho OCR variant
    "ivdejulho": ("4dejulho", "PI"),
    # Remo / Náutico long forms
    "clubederemo": ("remo", None),
    "nauticocapibaribe": ("nautico", None),
    # Gama (DF)
    "segama": ("gama", None),
    # Macaé
    "macaesportefc": ("macaesporte", None),
    # Tolima (Colombia)
    "deportestolima": ("tolima", None),
    # Red Bull Brasil / Red Bull Bragantino == Bragantino (SP)
    "redbullbrasil": ("bragantino", "SP"),
    "redbullbragantino": ("bragantino", "SP"),
}

# Default state for famous clubs whose bare name appears in data while
# other (lesser) clubs share the base name with a state suffix.
DEFAULT_STATE: dict[str, str] = {
    "santos": "SP",
    "vasco": "RJ",
    "botafogo": "RJ",
    "flamengo": "RJ",
    "fluminense": "RJ",
    "atletico": "MG",
    "america": "MG",
    "internacional": "RS",
    "vitoria": "BA",
    "sport": "PE",
    "santacruz": "PE",
    "guarani": "SP",
    "bragantino": "SP",
    "saoraimundo": "RR",
    "nautico": "PE",
    "juventude": "RS",
    "portuguesa": "SP",
    "ypiranga": "RS",
}

# Friendly display names for clubs where the most frequent raw form is
# awkward or ambiguous.
DISPLAY_OVERRIDES: dict[str, str] = {
    "brasil": "Brasil de Pelotas",
    "4dejulho": "4 de Julho",
    "saojose": "São José-RS",
    "desportiva": "Desportiva-ES",
    "gama": "Gama-DF",
    "internacional|SC": "Internacional-SC",
    "guarani|SP": "Guarani-SP",
    "atletico|MG": "Atlético-MG",
    "atletico|PR": "Athletico-PR",
    "atletico|GO": "Atlético-GO",
    "america|MG": "América-MG",
    "america|RN": "América-RN",
    "cuiaba": "Cuiabá",
}

_CODE_AT_END = re.compile(
    r"^(?P<base>.*?)[\s\-–—]+\(?(?P<code>[A-Z]{2,3})\)?\s*$"
)


def strip_accents(text: str) -> str:
    """Remove diacritics: 'São Paulo' -> 'Sao Paulo'."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )


def canonical_key(text: str) -> str:
    """Accent/punctuation-insensitive key used for all name matching.

    "A.b.c." -> "abc"; "EC Bahia" -> "bahia"; "Vitoria F. C." -> "vitoria".
    Initialisms like "F. C." are re-merged into "fc" before the generic
    club-type tokens (fc/ec/sc/ac/cf/ca) are stripped from both ends.
    """
    s = strip_accents(text).lower().replace(".", " ")
    tokens = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    merged: list[str] = []
    run = ""
    for t in tokens:
        if len(t) == 1:
            run += t
        else:
            if run:
                merged.append(run)
                run = ""
            merged.append(t)
    if run:
        merged.append(run)
    while merged and merged[0] in _CLUB_TOKENS:
        merged = merged[1:]
    while merged and merged[-1] in _CLUB_TOKENS:
        merged = merged[:-1]
    return "".join(merged)


def parse_team_name(raw: str) -> tuple[str, str | None]:
    """Split a raw team name into ``(base, code)``.

    ``code`` is a Brazilian state ("SP"), a country code ("URU") or None.
    Handles "Palmeiras-SP", "Atlético - MG", "America MG", "River (PI)",
    "Nacional (URU)", "Barcelona-EQU", "Boavista Sport Club (...) - RJ".
    """
    s = raw.strip()
    # Drop parenthetical annotations that are not a bare trailing code,
    # e.g. "(antigo Esporte Clube Barreira)".
    s = re.sub(r"\((?!\s*[A-Z]{2,3}\s*\))[^)]*\)", " ", s).strip()
    m = _CODE_AT_END.match(s)
    if m:
        code = m.group("code")
        base = m.group("base").strip(" -–—")
        if code in CODES and canonical_key(base):
            return base, code
    return s, None


def parse_date(raw: str | None) -> date | None:
    """Parse ISO, ISO+time and Brazilian DD/MM/YYYY dates."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(raw: str | None) -> str | None:
    """Normalize a kick-off time like '18:30:00' to '18:30'."""
    if not raw:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})", str(raw).strip())
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def parse_int(raw) -> int | None:
    """Parse an int tolerating blanks and float-formatted CSV values."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_float(raw):
    if raw is None:
        return None
    s = str(raw).strip().rstrip("%")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def resolve_alias(base_key: str) -> tuple[str, str | None]:
    """Apply curated alias corrections to a canonical base key."""
    return ALIASES.get(base_key, (base_key, None))


def has_accent(text: str) -> bool:
    return any(unicodedata.combining(ch)
               for ch in unicodedata.normalize("NFKD", text))


class TeamRegistry:
    """Assigns stable canonical keys and display names to team names.

    Usage: ``register`` every raw name seen in the match datasets first
    (so ambiguity is judged on real match data), then register player-club
    names from FIFA data, then call ``finalize``.  After finalization,
    ``key_for(raw)`` and ``display(key)`` are stable for all queries.
    """

    def __init__(self) -> None:
        self._variants: dict[tuple[str, str | None], list[str]] = {}
        self._raw_cache: dict[str, str] = {}
        self._display: dict[str, str] = {}
        self.finalized = False

    # -- registration ----------------------------------------------------

    def register(self, raw: str) -> None:
        """Record a raw team/club name (idempotent)."""
        raw = raw.strip()
        base, code = parse_team_name(raw)
        base_key, forced = resolve_alias(canonical_key(base))
        code = forced or code
        raws = self._variants.setdefault((base_key, code), [])
        if raw not in raws:
            raws.append(raw)

    # -- finalization ----------------------------------------------------

    def finalize(self) -> None:
        """Resolve base-name ambiguity and compute display names."""
        # Which base names carry more than one Brazilian state?
        states_by_base: dict[str, set[str]] = {}
        for (base_key, code) in self._variants:
            if code in BR_STATES:
                states_by_base.setdefault(base_key, set()).add(code)

        # Map every (base_key, code) variant to its final canonical key and
        # merge the raw display candidates of variants sharing one key.
        merged: dict[str, tuple[str, str | None, list[str]]] = {}
        for (base_key, code), raws in self._variants.items():
            states = states_by_base.get(base_key, set())
            if code in COUNTRY_CODES:
                key = f"{base_key}|{code}"          # country is identity
                eff = code
            elif len(states) >= 2:
                eff = code if code in BR_STATES else DEFAULT_STATE.get(base_key)
                key = f"{base_key}|{eff}" if eff else base_key
            else:
                key = base_key                       # unambiguous: drop state
                eff = None
            if key in merged:
                merged[key][2].extend(raws)
            else:
                merged[key] = (base_key, eff, list(raws))

        self._display = {}
        self._raw_cache = {}
        for key, (base_key, eff, raws) in merged.items():
            self._display[key] = (DISPLAY_OVERRIDES.get(key)
                                  or self._pick_display(base_key, eff, key, raws))
            for raw in raws:
                self._raw_cache[raw] = key
        self.finalized = True

    def _pick_display(self, base_key: str, eff: str | None, key: str,
                      raws: list[str]) -> str:
        """Choose a display name from all raw variants of one final key."""
        counts: dict[str, int] = {}
        for raw in raws:
            base, _ = parse_team_name(raw)
            counts[base] = counts.get(base, 0) + 1
        if not counts:
            base_name = key
        else:
            base_name = max(counts.items(), key=self._display_rank)[0].strip()
        if eff in COUNTRY_CODES:
            return f"{base_name} ({eff})"
        if eff in BR_STATES:
            base_name = f"{base_name}-{eff}"
        return base_name

    @staticmethod
    def _display_rank(item: tuple[str, int]):
        name, n = item
        # Prefer accented forms, then more frequent, then fewer/shorter words
        # ("Juventude" over "EC Juventude", "CSA" over "CS Alagoano").
        return (has_accent(name), n, -len(name.split()), -len(name), name)

    # -- lookup ----------------------------------------------------------

    def key_for(self, raw: str) -> str:
        """Canonical key for a raw name (registers it if unseen)."""
        raw = raw.strip()
        if raw in self._raw_cache:
            return self._raw_cache[raw]
        if self.finalized:
            base, code = parse_team_name(raw)
            base_key, forced = resolve_alias(canonical_key(base))
            code = forced or code
            states = {c for (b, c) in self._variants if b == base_key and c in BR_STATES}
            if code in COUNTRY_CODES:
                key = f"{base_key}|{code}"
            elif len(states) >= 2:
                eff = code if code in BR_STATES else DEFAULT_STATE.get(base_key)
                key = f"{base_key}|{eff}" if eff else base_key
            else:
                key = base_key
            self._raw_cache[raw] = key
            return key
        self.register(raw)
        return self.key_for(raw) if self.finalized else raw

    def display(self, key: str) -> str:
        return self._display.get(key, key)

    def display_names(self) -> dict[str, str]:
        """Canonical key -> display name (read-only copy)."""
        return dict(self._display)

    def display_name_for(self, raw: str) -> str:
        return self.display(self.key_for(raw))

    def keys(self) -> list[str]:
        return sorted(self._display)
