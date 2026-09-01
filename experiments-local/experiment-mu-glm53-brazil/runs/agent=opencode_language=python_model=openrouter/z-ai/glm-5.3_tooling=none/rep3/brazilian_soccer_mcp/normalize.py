"""
Normalization utilities for the Brazilian Soccer MCP server.

Context block
-------------
Why:
    The six Kaggle datasets that feed this server were produced by different
    authors and use wildly inconsistent conventions for team names
    ("Palmeiras-SP", "Palmeiras", "Vasco da Gama - RJ", "Sport Club do Recife",
    "Athletico Paranaense - PR", ...), dates ("2023-09-24",
    "2012-05-19 18:30:00", "29/03/2003"), numbers ("2", "2.0", "NA") and
    competition names.  Every query path funnels through this module so the
    rest of the system only ever sees canonical values.

What:
    * ``fold_accents``   - Unicode NFKD accent folding to ASCII.
    * ``parse_date``     - multi-format date parsing -> ``datetime.date``.
    * ``parse_int``      - tolerant integer parsing -> ``int | None``.
    * ``TeamName``       - immutable (base, state) identity for a team string.
    * ``normalize_team`` - raw team string -> ``TeamName`` with alias mapping.
    * ``resolve_competition`` - free-text competition -> canonical name.
    * ``canonical_display_name`` - curated pretty names for major clubs.

Test:
    Unit-tested in ``tests/test_normalize.py`` (BDD GWT scenarios) covering
    state-suffix stripping, parenthetical retention, alias mapping and every
    date/number format found in the raw CSVs.

Spec references:
    TASK.md "Data Quality Notes" - team name variations, date formats,
    character encoding (UTF-8 handling happens implicitly: every CSV is
    opened with ``encoding="utf-8"`` and names are folded via NFKD).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: The 27 Brazilian federative-unit abbreviations (UF codes).  A trailing
#: token matching one of these marks the team's state (e.g. "Palmeiras-SP").
UF_CODES: frozenset[str] = frozenset(
    [
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    ]
)

#: Canonical competition names used throughout the system.
COMPETITIONS = {
    "brasileirao-serie-a": "Brasileirão Serie A",
    "brasileirao-serie-b": "Brasileirão Serie B",
    "brasileirao-serie-c": "Brasileirão Serie C",
    "copa-do-brasil": "Copa do Brasil",
    "copa-libertadores": "Copa Libertadores",
}

#: Accepted free-text aliases -> canonical competition keys.
_COMPETITION_ALIASES: dict[str, str] = {
    "seriea": "brasileirao-serie-a",
    "serie-a": "brasileirao-serie-a",
    "seriaa": "brasileirao-serie-a",
    "brasileirao": "brasileirao-serie-a",
    "brasileiraoa": "brasileirao-serie-a",
    "brasileiranserieaa": "brasileirao-serie-a",
    "campeonatobrasileiro": "brasileirao-serie-a",
    "campeonatobrasileiroseriea": "brasileirao-serie-a",
    "serieb": "brasileirao-serie-b",
    "serie-b": "brasileirao-serie-b",
    "brasileiraob": "brasileirao-serie-b",
    "seriec": "brasileirao-serie-c",
    "serie-c": "brasileirao-serie-c",
    "copadobrasil": "copa-do-brasil",
    "cdb": "copa-do-brasil",
    "copabrasil": "copa-do-brasil",
    "braziliancup": "copa-do-brasil",
    "libertadores": "copa-libertadores",
    "copalibertadores": "copa-libertadores",
    "copaconmebol": "copa-libertadores",
    "conmebollibertadores": "copa-libertadores",
}

# --------------------------------------------------------------------------
# Team-name aliases
# --------------------------------------------------------------------------

#: base -> (canonical base, fallback state).  Applied after state-suffix
#: stripping; an explicit state on the raw name always wins over the alias
#: fallback.  This is what merges cross-dataset spellings of the same club
#: (e.g. "Vasco da Gama-RJ" vs "Vasco", "Atlético Mineiro" vs "Atlético-MG").
TEAM_ALIASES: dict[str, tuple[str, str | None]] = {
    # Vasco da Gama (RJ) - spelled "Vasco" in novo, "Vasco da Gama" elsewhere.
    "vascodagama": ("vasco", "RJ"),
    # Atlético clubs: full names collapse onto the state-qualified base.
    "atleticomineiro": ("atletico", "MG"),
    "atleticoparanaense": ("atletico", "PR"),
    "athleticoparanaense": ("atletico", "PR"),
    "atleticogoianiense": ("atletico", "GO"),
    "atleticogo": ("atletico", "GO"),
    # "Athletico" (rebranded 2019 spelling) always means the Paranaense club;
    # bare occurrences in Libertadores data carry no state suffix at all.
    "athletico": ("atletico", "PR"),
    "athleticopr": ("atletico", "PR"),
    # Sport Club do Recife.
    "sportclubdorecife": ("sport", "PE"),
    "sportrecife": ("sport", "PE"),
    "sportclubrecife": ("sport", "PE"),
    # Ceará Sporting Club.
    "cearasportingclub": ("ceara", "CE"),
    "cearasc": ("ceara", "CE"),
    # América clubs (FIFA spells them with parenthetical qualifiers).
    "americafc": ("america", "MG"),
    "americafcminasgerais": ("america", "MG"),
    "americafcnatal": ("america", "RN"),
    "americadenatal": ("america", "RN"),
    "americarn": ("america", "RN"),
    "americamg": ("america", "MG"),
    # EC Bahia (BR-Football spelling).
    "ecbahia": ("bahia", "BA"),
    "bahia_fc": ("bahia", "BA"),
    # Goiás Esporte Clube.
    "goiasesporteclube": ("goias", "GO"),
    # Red Bull Bragantino long forms.
    "redbullbragantino": ("redbullbragantino", "SP"),
    "rbbragantino": ("redbullbragantino", "SP"),
    # Grêmio Foot-Ball Porto Alegrense full name.
    "gremiofootballportoalegrense": ("gremio", "RS"),
    # Clube de Regatas do Flamengo full name.
    "clubederegatasdoflamengo": ("flamengo", "RJ"),
    # Fortaleza Esporte Clube.
    "fortalezaesporteclube": ("fortaleza", "CE"),
    # Cruzeiro Esporte Clube.
    "cruzeiroesporteclube": ("cruzeiro", "MG"),
    # Sociedade Esportiva Palmeiras full name.
    "sociedadeesportivapalmeiras": ("palmeiras", "SP"),
    # Sport Club Corinthians Paulista full name.
    "sportclubcorinthianspaulista": ("corinthians", "SP"),
    # São Paulo Futebol Clube full name.
    "saopaulofutebolclube": ("saopaulo", "SP"),
    # Fluminense Football Club full name.
    "fluminensefootballclub": ("fluminense", "RJ"),
    # Botafogo de Futebol e Regatas full name.
    "botafogodefuteboleregatas": ("botafogo", "RJ"),
    # BR-Football spells many clubs with generic FC/EC affixes or short
    # forms while the dedicated files use the state-suffixed short name.
    "fortalezafc": ("fortaleza", "CE"),
    "fortalezaec": ("fortaleza", "CE"),
    "bragantino": ("redbullbragantino", "SP"),
    "ecjuventude": ("juventude", "RS"),
    "ecvitoria": ("vitoria", "BA"),
    "vitoriaec": ("vitoria", "BA"),
    "csalagoano": ("csa", "AL"),
    "nauticocapibaribe": ("nautico", "PE"),
    "portuguesadesportos": ("portuguesa", "SP"),
    "caparana": ("parana", "PR"),
    "santacruzfc": ("santacruz", "PE"),
    "fcatleticocearense": ("atleticocearense", "CE"),
    "clubedoremo": ("remo", "PA"),
    "gremionovorizontino": ("novorizontino", "SP"),
    "ecinternacional": ("internacional", "SC"),
    "sercaxias": ("caxias", "RS"),
    "operariofc": ("operario", "MS"),
    "operarioferroviarioesportec": ("operario", "PR"),
    "brasildepelotas": ("brasil", "RS"),
    "saojosepoa": ("saojose", "RS"),
}

#: Bases whose state-less variants must NOT be folded into a same-base
#: state-qualified club: "River Plate" without a state is the famous
#: Argentine club (Libertadores/FIFA data), while "River Plate - SE" in the
#: Copa do Brasil file is an unrelated Brazilian minnow.
NO_MERGE_BASES: frozenset[str] = frozenset({"riverplate"})

#: Curated display names for the best-known clubs, keyed by "base|state".
#: Anything not listed falls back to the most frequently seen raw spelling.
DISPLAY_NAMES: dict[str, str] = {
    "palmeiras|SP": "Palmeiras",
    "corinthians|SP": "Corinthians",
    "saopaulo|SP": "São Paulo",
    "santos|SP": "Santos",
    "pontepreta|SP": "Ponte Preta",
    "portuguesa|SP": "Portuguesa",
    "redbullbragantino|SP": "Red Bull Bragantino",
    "flamengo|RJ": "Flamengo",
    "fluminense|RJ": "Fluminense",
    "vasco|RJ": "Vasco da Gama",
    "botafogo|RJ": "Botafogo",
    "gremio|RS": "Grêmio",
    "internacional|RS": "Internacional",
    "juventude|RS": "Juventude",
    "atletico|MG": "Atlético Mineiro",
    "cruzeiro|MG": "Cruzeiro",
    "america|MG": "América Mineiro",
    "atletico|PR": "Athletico Paranaense",
    "coritiba|PR": "Coritiba",
    "parana|PR": "Paraná",
    "atletico|GO": "Atlético Goianiense",
    "goias|GO": "Goiás",
    "sport|PE": "Sport Recife",
    "nautico|PE": "Náutico",
    "santacruz|PE": "Santa Cruz",
    "bahia|BA": "Bahia",
    "vitoria|BA": "Vitória",
    "ceara|CE": "Ceará",
    "fortaleza|CE": "Fortaleza",
    "chapecoense|SC": "Chapecoense",
    "avai|SC": "Avaí",
    "figueirense|SC": "Figueirense",
    "criciuma|SC": "Criciúma",
    "joinville|SC": "Joinville",
    "cuiaba|MT": "Cuiabá",
    "csa|AL": "CSA",
    "brasiliense|DF": "Brasiliense",
    "gremiobarueri|SP": "Grêmio Barueri",
    "internacional|SC": "Internacional-SC",
    "atletico|AC": "Atlético Acreano",
    "atletico|ES": "Atlético Capixaba",
    "atletico|BA": "Atlético de Alagoinhas",
    "flamengo|PI": "Flamengo-PI",
    "santos|AP": "Santos-AP",
    "botafogo|PB": "Botafogo-PB",
}

# --------------------------------------------------------------------------
# Basic scalar normalization
# --------------------------------------------------------------------------


def fold_accents(value: str) -> str:
    """Fold accented characters to their ASCII base (São Paulo -> Sao Paulo)."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_date(raw: object) -> date | None:
    """Parse the date formats present across the datasets.

    Handles ISO dates with/without time ("2023-09-24",
    "2012-05-19 18:30:00") and Brazilian DD/MM/YYYY ("29/03/2003").
    Returns ``None`` for blanks, "NA" and anything unparseable.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    # "29/03/2003 16:00" - csv cells sometimes glue a time on.
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(raw: object) -> int | None:
    """Parse goal counts etc. that appear as int, float-ish or 'NA' strings."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw) if raw == int(raw) else None
    text = str(raw).strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(raw: object) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Team-name normalization
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TeamName:
    """Normalized team identity: space-free base plus optional UF state."""

    base: str
    state: str | None = None

    @property
    def key(self) -> str:
        return f"{self.base}|{self.state}" if self.state else f"{self.base}|"


def normalize_team(raw: str) -> TeamName:
    """Normalize a raw team string to a ``TeamName``.

    Rules, in order:
      1. Accent-fold and lowercase.
      2. Parentheses become spaces (content is *kept* so that foreign
         qualifiers like "Nacional (URU)" vs "Nacional (PAR)" stay distinct).
      3. All remaining punctuation becomes spaces; tokens are joined
         without spaces ("Sport Club do Recife" -> "sportclubdorecife").
      4. A trailing UF token is lifted out as the state
         ("América - MG" -> base "america", state "MG").
      5. ``TEAM_ALIASES`` remaps the base to its canonical club identity.
    """
    if not raw:
        return TeamName("", None)
    text = fold_accents(str(raw)).lower()
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [t for t in text.split() if t]
    state: str | None = None
    if tokens and tokens[-1].upper() in UF_CODES:
        state = tokens[-1].upper()
        tokens = tokens[:-1]
    base = "".join(tokens)
    alias = TEAM_ALIASES.get(base)
    if alias:
        base, alias_state = alias
        state = state or alias_state
    return TeamName(base, state)


# --------------------------------------------------------------------------
# Competition normalization
# --------------------------------------------------------------------------


def resolve_competition(raw: object) -> str | None:
    """Map free text ("serie a", "Libertadores", "CdB") to a canonical name."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    folded = re.sub(r"[^a-z0-9]+", "", fold_accents(text).lower())
    for alias, key in _COMPETITION_ALIASES.items():
        if folded == alias:
            return COMPETITIONS[key]
    # Also accept the canonical names themselves.
    for key, canonical in COMPETITIONS.items():
        if folded == key.replace("-", "") or fold_accents(text).lower() == fold_accents(canonical).lower():
            return canonical
    return None


def canonical_display_name(club_key: str, fallback: str) -> str:
    """Return a curated display name for a club key, or the fallback."""
    return DISPLAY_NAMES.get(club_key, fallback)
