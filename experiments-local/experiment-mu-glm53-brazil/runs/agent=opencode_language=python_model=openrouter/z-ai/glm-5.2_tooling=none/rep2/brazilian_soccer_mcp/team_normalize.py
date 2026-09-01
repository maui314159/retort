# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# Module: brazilian_soccer_mcp.team_normalize
# Purpose: Map the many spelling variants of Brazilian club names that appear
# across the six Kaggle CSV files onto one canonical key. The datasets differ:
#   * Brasileirao_Matches.csv      -> "Palmeiras-SP", "Atletico-MG"
#   * Brazilian_Cup_Matches.csv    -> "América - MG", "Boavista Sport Club (...)
#   * Libertadores_Matches.csv      -> "Barcelona-EQU", "Nacional (URU)"
#   * BR-Football-Dataset.csv      -> "Sao Paulo", "Gremio" (ASCII, no accents)
#   * novo_campeonato_brasileiro.csv -> "Guarani", "Sport Club Corinthians Paulista"
#   * fifa_data.csv                -> "Clube de Regatas do Flamengo", "SE Palmeiras"
# A canonical key lets a single query ("Flamengo") match rows in every file.
# Strategy:
#   1. strip accents + lowercase + collapse whitespace
#   2. drop trailing "-<STATE>" / "-<COUNTRY>" suffixes and "(<COUNTRY>)" tags
#   3. apply an explicit alias table for known full-name / abbreviation variants
#   4. fall back to a best-effort fuzzy key on unknown names
# --------------------------------------------------------------------------- #
"""Canonical team-name normalization for cross-file matching."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Explicit alias table. Keys/values are already in canonical (ascii, lower)
# form. Each entry maps an alias -> canonical key. Multiple aliases may point
# to the same canonical key. This is intentionally hand-curated for the clubs
# that appear in the provided datasets.
_ALIAS_TABLE: dict[str, str] = {
    # Flamengo
    "flamengo": "flamengo",
    "clube de regatas do flamengo": "flamengo",
    "cr flamengo": "flamengo",
    "flamengo rj": "flamengo",
    # Fluminense
    "fluminense": "fluminense",
    "fluminense rj": "fluminense",
    # Corinthians
    "corinthians": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "sccp": "corinthians",
    "spcc": "corinthians",
    # Palmeiras
    "palmeiras": "palmeiras",
    "se palmeiras": "palmeiras",
    "sociedade esportiva palmeiras": "palmeiras",
    "palmeiras sp": "palmeiras",
    # São Paulo
    "sao paulo": "sao paulo",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "spfc": "sao paulo",
    "sao paulo sp": "sao paulo",
    # Santos
    "santos": "santos",
    "santos fc": "santos",
    "santos futebol clube": "santos",
    "santos sp": "santos",
    # Grêmio
    "gremio": "gremio",
    "gremio fbpa": "gremio",
    "gremio rs": "gremio",
    # Internacional / Inter
    "internacional": "internacional",
    "inter rs": "internacional",
    "internacional rs": "internacional",
    "sci": "internacional",
    # Atlético Mineiro
    "atletico mg": "atletico-mg",
    "atletico-mg": "atletico-mg",
    "clube atletico mineiro": "atletico-mg",
    "cam": "atletico-mg",
    # Cruzeiro
    "cruzeiro": "cruzeiro",
    "cruzeiro mg": "cruzeiro",
    # Botafogo
    "botafogo": "botafogo",
    "botafogo rj": "botafogo",
    "botafogo fr": "botafogo",
    # Vasco
    "vasco": "vasco",
    "vasco da gama": "vasco",
    "vasco rj": "vasco",
    # Cruzeiro/Atletico-PR disambiguation
    "atletico pr": "atletico-pr",
    "atletico-pr": "atletico-pr",
    "clube atletico paranaense": "atletico-pr",
    "coritiba": "coritiba",
    "coritiba fc": "coritiba",
    "cfc": "coritiba",
    # Bahia / Vitória
    "bahia": "bahia",
    "bahia ec": "bahia",
    "vitoria": "vitoria",
    "vitoria ba": "vitoria",
    "esporte clube vitoria": "vitoria",
    # Fortaleza / Ceará
    "fortaleza": "fortaleza",
    "fortaleza ec": "fortaleza",
    "ceara": "ceara",
    "ceara sc": "ceara",
    # Sport / Náutico / Santa Cruz (Pernambuco)
    "sport": "sport",
    "sport pe": "sport",
    "sport club do recife": "sport",
    "sport recife": "sport",
    "nautico": "nautico",
    "nautico pe": "nautico",
    "santa cruz": "santa cruz",
    # Goiás / Goiânia clubs
    "goias": "goias",
    "goias ec": "goias",
    "atletico go": "atletico-go",
    "atletico-go": "atletico-go",
    "gremio anapolis": "gremio anapolis",
    # Juventude / Caxias
    "juventude": "juventude",
    "caxias": "caxias",
    # Avaí / Figueirense (Santa Catarina)
    "avai": "avai",
    "figueirense": "figueirense",
    # Portuguesa
    "portuguesa": "portuguesa",
    "portuguesa sp": "portuguesa",
    # Ponte Preta
    "ponte preta": "ponte preta",
    "ponte preta sp": "ponte preta",
    "aa ponte preta": "ponte preta",
    # Guarani / Bragantino
    "guarani": "guarani",
    "guarani sp": "guarani",
    "red bull bragantino": "bragantino",
    "bragantino": "bragantino",
    "rb bragantino": "bragantino",
    # América-MG / América-RJ
    "america mg": "america-mg",
    "america-mg": "america-mg",
    "america rj": "america-rj",
    "america-rj": "america-rj",
    "america-rn": "america-rn",
    "america rn": "america-rn",
    "america": "america",  # ambiguous fallback; disambiguated by caller if needed
    # Chapecoense
    "chapecoense": "chapecoense",
    # Atlético-GO vs Atlético-MG keep distinct; "Atletico Goianiense" alias
    "atletico goianiense": "atletico-go",
    # Cuiabá
    "cuiaba": "cuiaba",
    "cuiaba ec": "cuiaba",
    # Athletico-PR (alternative spelling in some datasets)
    "athletico pr": "atletico-pr",
    "athletico-paranaense": "atletico-pr",
    "club athletico paranaense": "atletico-pr",
    # Operário / Londrina / Paraná clubs
    "operario": "operario",
    "operario pr": "operario",
    "londrina": "londrina",
    # CSA / CRB (Alagoas)
    "csa": "csa",
    "crb": "crb",
    # Brasil de Pelotas / Grêmio (RS lower divisions) kept distinct
    "brasil de pelotas": "brasil de pelotas",
    # Oeste / Novorizontino (SP)
    "oeste": "oeste",
    "novorizontino": "novorizontino",
    # Confiança / Sergipe
    "confianca": "confianca",
    # Foreign clubs that show up in Libertadores (kept verbatim, canonical key)
    "barcelona": "barcelona",
    "barcelona equ": "barcelona",
    "barcelona sc": "barcelona",
    "nacional uru": "nacional-uru",
    "nacional (uru)": "nacional-uru",
    "nacional": "nacional",
    "bolivar": "bolivar",
    "bolivar bol": "bolivar",
    # Suffix-stripped "america - mg" form seen in Brazilian_Cup_Matches
    "america - mg": "america-mg",
    "america - rj": "america-rj",
    # FIFA dataset full-name variants (accented in source, ASCII after strip)
    "atletico mineiro": "atletico-mg",
    "atletico paranaense": "atletico-pr",
    "ceara sporting club": "ceara",
    "parana": "parana",
    "america fc (minas gerais)": "america-mg",
    "america (minas gerais)": "america-mg",
}


_STATE_TOKENS = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}

_COUNTRY_TOKENS = {
    "uru", "par", "arg", "chi", "bol", "equ", "col", "per", "ven",
    "bra", "mex", "ec",
}

# Suffixes commonly found in club names that we strip before alias lookup.
_NAME_NOISE_TOKENS = {
    "sc", "fc", "ec", "acr", "cr", "ac", "clube", "club", "de", "do", "da",
    "dos", "das", "e", "futebol", "clube", "socio", "atletico", "esporte",
    "sociedade", "regatas", "clube", "paulista", "goianiense", "mineiro",
}

_TRAILING_SUFFIX_RE = re.compile(r"\s*-\s*([a-z]{2,3})\s*$")
_PARENS_COUNTRY_RE = re.compile(r"\s*\(([^)]+)\)\s*$")

# Tokens stripped in the second-pass fallback for names that did not hit the
# alias table on the first pass. These are generic club-designator words that
# the FIFA dataset appends; stripping them recovers the bare club name. City
# qualifiers like "mineiro"/"paranaense" are NOT here because they are kept as
# disambiguators (Atletico-MG vs Atletico-PR).
_NOISE_TOKENS = {
    "sc", "fc", "ec", "acr", "cr", "ac", "clube", "club", "socio", "esporte",
    "futebol", "regatas", "sporting", "of", "the", "do", "da", "de", "dos",
    "das", "e", "clube", "s.a", "sa",
}


def _strip_parens(text: str) -> str:
    """Remove all parenthesized substrings from *text*."""
    return re.sub(r"\s*\([^)]*\)\s*", " ", text).strip()


def _strip_accents(text: str) -> str:
    """Return *text* with accents removed, NFKD-decomposed, ASCII-only."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _drop_trailing_state_or_country(text: str) -> str:
    """Remove a trailing ``-SP`` / ``-MG`` / ``-EQU`` style suffix.

    Keeps the original name otherwise. Runs iteratively in case of double
    suffixes like ``"América - MG"``.
    """
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        m = _TRAILING_SUFFIX_RE.search(cur)
        if m and m.group(1) in _STATE_TOKENS | _COUNTRY_TOKENS:
            cur = cur[: m.start()].strip()
    return cur


def _drop_parens_country(text: str) -> str:
    """Strip a trailing ``"(URU)"`` / ``"(EQU)"`` country tag."""
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        m = _PARENS_COUNTRY_RE.search(cur)
        if m and m.group(1).lower() in _COUNTRY_TOKENS:
            cur = cur[: m.start()].strip()
    return cur


@lru_cache(maxsize=4096)
def normalize_team(raw: str) -> str:
    """Return a canonical lowercase ASCII key for a team name.

    The key is stable across spelling variants so that a query for
    ``"Flamengo"`` matches ``"Flamengo-RJ"``, ``"Clube de Regatas do Flamengo"``
    and ``"flamengo rj"``.

    Examples:
        >>> normalize_team("Palmeiras-SP")
        'palmeiras'
        >>> normalize_team("Clube de Regatas do Flamengo")
        'flamengo'
        >>> normalize_team("América - MG")
        'america-mg'
        >>> normalize_team("Nacional (URU)")
        'nacional-uru'
    """
    if raw is None:
        return ""
    s = _strip_accents(str(raw)).lower().strip()
    if not s:
        return ""
    s = _collapse_ws(s)
    # 1. First-pass alias lookup on the bare accent-stripped form. This catches
    #    explicit full-name aliases like "nacional (uru)" before we start
    #    stripping the tags that distinguish them.
    if s in _ALIAS_TABLE:
        return _ALIAS_TABLE[s]
    # 2. Drop trailing "-SP"/"-EQU" and "(URU)" tags, then re-check the alias
    #    table. The alias table stores bare canonical forms for most clubs.
    s2 = _drop_parens_country(s)
    s2 = _drop_trailing_state_or_country(s2)
    s2 = _collapse_ws(s2)
    if s2 != s and s2 in _ALIAS_TABLE:
        return _ALIAS_TABLE[s2]
    # 3. Second-pass fallback: strip parenthesized descriptors and generic
    #    club-designator noise words, then re-check the alias table. Catches
    #    FIFA variants like "Ceará Sporting Club" -> "ceara" and
    #    "América FC (Minas Gerais)" -> "america" without bloating the alias
    #    table with every FIFA full name.
    stripped = _strip_parens(s2)
    tokens = [t for t in stripped.split() if t not in _NOISE_TOKENS]
    reduced = _collapse_ws(" ".join(tokens))
    if reduced and reduced in _ALIAS_TABLE:
        return _ALIAS_TABLE[reduced]
    if reduced and reduced != s2:
        return reduced
    return s2


def team_display_name(canonical: str) -> str:
    """Return a human-readable display name for a canonical key."""
    if not canonical:
        return ""
    return canonical.replace("-", " ").title()


# Curated set of traditional Brazilian derbies, keyed by canonical team pair
# joined with " x ". Order-independent: we sort the two keys before lookup.
DERBIES: set[frozenset[str]] = {
    frozenset({"flamengo", "fluminense"}),     # Fla-Flu
    frozenset({"flamengo", "vasco"}),           # Clássico da Multidão
    frozenset({"flamengo", "botafogo"}),        # Clássico da Rivalidade
    frozenset({"fluminense", "botafogo"}),      # PFAC
    frozenset({"palmeiras", "corinthians"}),    # Derby Paulista
    frozenset({"sao paulo", "corinthians"}),    # Majestoso
    frozenset({"sao paulo", "palmeiras"}),       # Choque-Rei
    frozenset({"santos", "sao paulo"}),          # San-São
    frozenset({"santos", "corinthians"}),        # Alvinegro praiano
    frozenset({"gremio", "internacional"}),     # Grenal
    frozenset({"atletico-mg", "cruzeiro"}),      # Clássico Mineiro
    frozenset({"bahia", "vitoria"}),             # Ba-Vi
    frozenset({"fortaleza", "ceara"}),           # Clássico-Rei
    frozenset({"nautico", "sport"}),             # Clássico dos Clássicos
    frozenset({"avai", "figueirense"}),          # Clássico de Florianópolis
    frozenset({"coritiba", "atletico-pr"}),      # Atle-Tiba
    frozenset({"goias", "atletico-go"}),         # Go-Go
}


def is_derby(team_a: str, team_b: str) -> bool:
    """True when the two (canonical) teams are a traditional derby pair."""
    return frozenset({normalize_team(team_a), normalize_team(team_b)}) in DERBIES
