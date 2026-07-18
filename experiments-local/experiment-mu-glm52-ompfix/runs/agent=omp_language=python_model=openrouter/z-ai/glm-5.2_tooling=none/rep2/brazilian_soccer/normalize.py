# brazilian_soccer.normalize
# -----------------------------------------------------------------------------
# Context:
#   The bundled Kaggle datasets use wildly inconsistent team-naming conventions
#   (see TASK.md "Data Quality Notes"):
#     * with a state suffix, no space:  "Palmeiras-SP", "Flamengo-RJ"
#     * with a state suffix, spaces:    "America - MG", "Boavista ... - RJ"
#     * with parenthetical notes:       "Nacional (URU)", "Barcelona-EQU",
#                                       "Boavista Sport Club (antigo ...) - RJ"
#     * full/official names:            "Sport Club Corinthians Paulista"
#   Brazilian Portuguese text also carries accents (Sao Paulo, Gremio, Avai) and
#   a cedilla (Fortaleza). To answer cross-file queries ("which competitions has
#   Palmeiras played in?") we must collapse all of these variants onto one key.
#
# What this module provides:
#   * normalize_team(name)        -> display name, accents kept, suffix/notes gone
#   * team_key(name)              -> accent-folded lowercased key for matching
#   * STATE_CODES                 -> the 27 Brazilian UF codes (+ a few foreign)
#   * DERBIES                     -> canonical Brazilian rivalries (for derby queries)
# -----------------------------------------------------------------------------
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# 27 Brazilian state codes (UF). A couple of foreign codes seen in the
# Libertadores dataset (URU, EQU, ARG, PAR, CHI, COL, PER, BOL, VEN) are also
# accepted so suffixes like "Barcelona-EQU" are stripped cleanly.
STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
    # foreign suffixes occasionally appended in the Libertadores dataset
    "URU", "EQU", "ARG", "PAR", "CHI", "COL", "PER", "BOL", "VEN",
}

# Trailing "-XX" / " - XX" where XX is a 2..3 letter state code.
_STATE_SUFFIX = re.compile(r"\s*-\s*([A-Z]{2,3})\s*$")
# Anything in parentheses, e.g. "(URU)" or "(antigo Esporte Clube Barreira)".
_PARENS = re.compile(r"\s*\([^)]*\)\s*")
# Repeated whitespace.
_WS = re.compile(r"\s+")


# Trailing "-XX" / " - XX" where XX is a 2..3 letter state code (case-insensitive:
# real data uses "Palmeiras-SP" but user queries may type "flamengo-rj").
_STATE_SUFFIX = re.compile(r"\s*-\s*([A-Za-z]{2,3})\s*$")

@lru_cache(maxsize=4096)
def _strip_suffix(value: str) -> str:
    """Remove a trailing state-code suffix, but only when it is a real code.

    This is conservative on purpose: a team literally named "ABC-RS" would not
    lose a real part of its name because we verify the code against STATE_CODES.
    """
    m = _STATE_SUFFIX.search(value)
    if m and m.group(1).upper() in STATE_CODES:
        return value[: m.start()].rstrip()
    return value


@lru_cache(maxsize=4096)
def normalize_team(name: object) -> str:
    """Return a clean display name: no parenthetical notes, no state suffix.

    Accents are preserved so the display name reads naturally ("São Paulo",
    "Grêmio", "Avaí", "América-MG" -> "América"). The input may be NaN/None.
    """
    if name is None:
        return ""
    s = str(name).strip()
    if not s or s.lower() in {"nan", "none"}:
        return ""
    # Repeatedly strip parens + suffixes (a name can carry both, in either form).
    for _ in range(3):
        prev = s
        s = _PARENS.sub(" ", s).strip()
        s = _strip_suffix(s).strip()
        s = _WS.sub(" ", s)
        if s == prev:
            break
    # Tidy a dangling trailing dash left by an unusual suffix.
    s = s.rstrip("-").strip()
    s = _WS.sub(" ", s)
    return s


@lru_cache(maxsize=4096)
def _fold(value: str) -> str:
    """Fold accents to ASCII (NFKD -> drop combining marks) and lowercase."""
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


@lru_cache(maxsize=4096)
def team_key(name: object) -> str:
    """Accent-folded, lowercased, suffix-free key used for robust matching.

    team_key("Palmeiras-SP")   == team_key("Palmeiras")
    team_key("Sao Paulo")      == team_key("São Paulo")
    team_key("America - MG")   == team_key("América-MG")
    """
    return _fold(normalize_team(name))


# Canonical Brazilian rivalries used by the derby queries. Keys are frozensets
# of team display names; values are the derby's common name. Matching is done on
# team_key(), so the spellings below are only representative.
DERBIES: dict[frozenset[str], str] = {
    frozenset({"Flamengo", "Fluminense"}): "Fla-Flu",
    frozenset({"Flamengo", "Vasco da Gama"}): "Clássico dos Milhões",
    frozenset({"Palmeiras", "Corinthians"}): "Clássico Maior",
    frozenset({"Corinthians", "São Paulo"}): "Majestoso",
    frozenset({"Palmeiras", "São Paulo"}): "Choque-Rei",
    frozenset({"Internacional", "Grêmio"}): "Gre-Nal",
    frozenset({"Atlético Mineiro", "Cruzeiro"}): "Clássico Mineiro",
    frozenset({"Athletico-PR", "Coritiba"}): "Atletiba",
    frozenset({"Bahia", "Vitória"}): "Ba-Vi",
    frozenset({"Sport", "Santa Cruz"}): "Clássico das Multidões",
    frozenset({"Fortaleza", "Ceará"}): "Clássico-Rei",
    frozenset({"Botafogo", "Vasco da Gama"}): "Clássico da Rivalidade",
    frozenset({"Náutico", "Sport"}): "Clássico dos Clássicos",
}

# Pre-compute a map from a frozenset of team_keys -> derby display name.
DERBY_KEYS: dict[frozenset[str], str] = {}
for _pair, _label in DERBIES.items():
    _a, _b = tuple(_pair)
    DERBY_KEYS[frozenset({team_key(_a), team_key(_b)})] = _label


def derby_name(team_a: object, team_b: object) -> str | None:
    """Return the derby name for a pair of teams, or None if they are not rivals."""
    return DERBY_KEYS.get(frozenset({team_key(team_a), team_key(team_b)}))
