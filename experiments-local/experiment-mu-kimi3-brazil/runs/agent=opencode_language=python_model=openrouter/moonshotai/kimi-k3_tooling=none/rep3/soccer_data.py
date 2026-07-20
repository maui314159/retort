"""Data layer for the Brazilian Soccer MCP server.

Loads the six Kaggle CSV datasets from ``data/kaggle/`` into a unified,
in-memory knowledge store:

* all five match files are normalised into a single match table with a
  common schema (date, teams, goals, competition, season, ...),
* the FIFA player file is exposed as a player table,
* team names are normalised (accents stripped, state/country suffixes
  removed, known aliases merged) so that "Palmeiras-SP", "Palmeiras" and
  "SE Palmeiras" style variants all resolve to the same entity,
* dates are parsed from every format used by the sources (ISO,
  ISO-with-time and Brazilian DD/MM/YYYY),
* cross-dataset duplicates (the same fixture appears in more than one
  file) are flagged so analytical queries can de-duplicate them.

Only the standard library and pandas are used.  Everything is loaded
lazily through :func:`get_store` and cached, so the first query pays the
(one-off, sub-second) load cost.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

# ---------------------------------------------------------------------------
# Canonical competition names
# ---------------------------------------------------------------------------
COMP_BRASILEIRAO = "Brasileirão Série A"
COMP_SERIE_B = "Brasileirão Série B"
COMP_SERIE_C = "Brasileirão Série C"
COMP_COPA_DO_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"

_BR_TOURNAMENT_MAP = {
    "serie a": COMP_BRASILEIRAO,
    "serie b": COMP_SERIE_B,
    "serie c": COMP_SERIE_C,
    "copa do brasil": COMP_COPA_DO_BRASIL,
}

# ---------------------------------------------------------------------------
# Team-name normalisation
# ---------------------------------------------------------------------------
_BR_STATES = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}
_COUNTRY_CODES = {
    "uru", "uruguay", "equ", "ecu", "ecuador", "arg", "argentina", "par",
    "paraguay", "per", "peru", "col", "colombia", "chi", "chile", "bol",
    "bolivia", "ven", "venezuela", "mex", "mexico", "bra", "esp", "por",
}

# Aliases map a *normalised* variant to the canonical *normalised* key.
_TEAM_ALIASES = {
    # --- disambiguation of state-suffixed homonyms (looked up before the
    # --- state token is stripped) ---
    "atletico pr": "athletico pr",
    "atletico es": "atletico es",
    "atletico go": "atletico go",
    "america rn": "america de natal",
    "botafogo pb": "botafogo pb",
    "botafogo sp": "botafogo sp",
    "guarani ce": "guarani de juazeiro",
    "internacional sc": "internacional sc",
    "ec internacional sc": "internacional sc",
    "ec internacional": "internacional sc",
    "nacional am": "nacional am",
    "river plate se": "river plate se",
    "santa cruz rn": "santa cruz rn",
    "santa cruz rs": "santa cruz rs",
    "sao jose pa": "sao jose pa",
    "sao jose rs": "sao jose rs",
    "vitoria es": "vitoria es",
    "vitoria f c es": "vitoria es",
    "vitoria f c": "vitoria es",
    # --- spelling variants of the same club ---
    "athletico": "athletico pr",
    "athletico paranaense": "athletico pr",
    "atletico paranaense": "athletico pr",
    "atletico": "atletico mg",
    "atletico mineiro": "atletico mg",
    "atletico goianiense": "atletico go",
    "america": "america mg",
    "america mineiro": "america mg",
    "america fc minas gerais": "america mg",
    "sport": "sport recife",
    "sport club do recife": "sport recife",
    "botafogo rj": "botafogo",
    "botafogo fr": "botafogo",
    "vasco": "vasco da gama",
    "ceara sporting club": "ceara",
    "fortaleza esporte clube": "fortaleza",
    "parana clube": "parana",
    "red bull bragantino": "bragantino",
    "flamengo rj": "flamengo",
    "santos fc": "santos",
    "corinthians paulista": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "gremio foot ball porto alegrense": "gremio",
    "sao paulo fc": "sao paulo",
    "goias ec": "goias",
    "ec vitoria": "vitoria",
    "vitoria ec": "vitoria",
    "vitoria f c": "vitoria",
    "sc internacional": "internacional",
    "ec bahia": "bahia",
    "fortaleza ec": "fortaleza",
    "fortaleza fc": "fortaleza",
    "ec juventude": "juventude",
    "abc": "abc",
    "csa": "csa",
    "crb": "crb",
    "crac": "crac",
    "asa": "asa",
    "4 de julho ec": "4 de julho",
    "afogados da ingazeira fc": "afogados",
    "america fc natal": "america de natal",
    "anapolis fc": "anapolis",
    "aquidauanense futebol clube": "aquidauanense",
    "boavista sc saquarema": "boavista",
    "boavista sport club": "boavista",
    "brasilia fc": "brasilia",
    "campinense clube": "campinense",
    "cordino ec": "cordino",
    "desportiva ferroviaria": "desportiva",
    "duque de caxias fc": "duque de caxias",
    "floresta ec": "floresta",
    "globo fc": "globo",
    "jaragua ec": "jaragua",
    "macae esporte fc": "macae esporte",
    "madureira ec": "madureira",
    "moto club de sao luis": "moto club",
    "moto clube": "moto club",
    "nautico capibaribe": "nautico",
    "nova mutum ec": "nova mutum",
    "operario fc": "operario",
    "operario ferroviario esporte c": "operario",
    "parnahyba s c": "parnahyba",
    "porto velho ec": "porto velho",
    "portuguesa desportos": "portuguesa",
    "real noroeste capixaba": "real noroeste",
    "retro fc brasil": "retro",
    "santa cruz fc": "santa cruz",
    "serra f c": "serra",
    "sinop fc": "sinop",
    "tocantinopolis ec": "tocantinopolis",
    "toledo ec": "toledo",
    "uniao de rondonopolis": "uniao rondonopolis",
    "vilhenense ec": "vilhenense",
    "xv piracicaba": "xv de piracicaba",
    "fc atletico cearense": "atletico cearense",
    "ce aimore": "aimore",
    "ser caxias": "caxias",
    "se gama": "gama",
    "sc genus": "genus",
    "ad frei paulistano": "frei paulistano",
}

_PARENS_RE = re.compile(r"\([^)]*\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_team(name: object) -> str:
    """Normalise a team name to a canonical matching key.

    Steps: accent stripping, lower-casing, removal of parenthesised
    qualifiers ("(antigo ...)"), punctuation -> space, removal of trailing
    Brazilian state or country codes, and alias resolution.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    text = _strip_accents(str(name)).lower()
    text = _PARENS_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    tokens = [tok for tok in _WS_RE.sub(" ", text).strip().split(" ") if tok]
    # "A B C" / "C R B" style letter-spaced acronyms -> "abc" / "crb".
    if len(tokens) > 1 and all(len(tok) == 1 for tok in tokens):
        tokens = ["".join(tokens)]
    # Resolve aliases on the full key first ("Atletico-PR" -> "atletico pr"
    # must become Athletico Paranaense *before* the state token is dropped,
    # otherwise it would collapse into "atletico" = Atlético Mineiro).
    key = _TEAM_ALIASES.get(" ".join(tokens))
    if key is not None:
        return key
    while tokens and tokens[-1] in _BR_STATES | _COUNTRY_CODES:
        tokens.pop()
    key = " ".join(tokens)
    return _TEAM_ALIASES.get(key, key)


def normalize_text(value: object) -> str:
    """Generic case/accent-insensitive normalisation for free-text matching."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return _strip_accents(str(value)).lower().strip()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
def parse_date(value: object) -> pd.Timestamp:
    """Parse the date formats used across the datasets.

    Supported: "2023-09-24", "2012-05-19 18:30:00", "29/03/2003".
    Returns ``pd.NaT`` for unparseable values.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return pd.Timestamp(pd.to_datetime(text, format=fmt)).normalize()
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(text, errors="coerce", dayfirst=True)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------
MATCH_COLUMNS = [
    "date", "season", "competition", "home_team", "away_team", "home_goals",
    "away_goals", "round", "stage", "venue", "source", "home_key",
    "away_key",
]


@dataclass
class SoccerStore:
    """In-memory knowledge store: unified matches + FIFA players."""

    matches: pd.DataFrame
    players: pd.DataFrame
    played_matches: pd.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        played = self.matches.dropna(subset=["home_goals", "away_goals"])
        self.played_matches = _dedupe_matches(played)


# When the same fixture appears in several files, prefer richer sources.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches": 0,
    "Brazilian_Cup_Matches": 0,
    "Libertadores_Matches": 0,
    "novo_campeonato_brasileiro": 1,
    "BR-Football-Dataset": 2,
}

# Sources disagree on kick-off dates by up to a day; fixtures repeated in
# reality (cup two-leg ties) are always weeks apart, so a 3-day window
# merges cross-source duplicates without ever touching real rematches.
_DEDUP_WINDOW = pd.Timedelta(days=3)


def _dedupe_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse fixtures recorded in more than one source file."""
    df = df.copy()
    df["_prio"] = df["source"].map(_SOURCE_PRIORITY).fillna(9).astype(int)
    group_cols = ["competition", "home_key", "away_key"]
    df = df.sort_values(group_cols + ["date", "_prio"], kind="mergesort")
    within_group_diff = df.groupby(group_cols, sort=False)["date"].diff()
    new_cluster = within_group_diff.isna() | (within_group_diff > _DEDUP_WINDOW)
    df["_cluster"] = new_cluster.groupby(
        [df[c] for c in group_cols], sort=False
    ).cumsum()
    df = df.sort_values(group_cols + ["_cluster", "_prio", "date"],
                        kind="mergesort")
    df = df.drop_duplicates(subset=group_cols + ["_cluster"], keep="first")
    df = df.drop(columns=["_prio", "_cluster"])
    return df.sort_values("date", kind="mergesort").reset_index(drop=True)


def _finalize_matches(df: pd.DataFrame, source: str) -> pd.DataFrame:
    df = df.copy()
    df["source"] = source
    df["home_key"] = df["home_team"].map(normalize_team)
    df["away_key"] = df["away_team"].map(normalize_team)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce").astype("Int64")
    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce").astype("Int64")
    for col in ("round", "stage", "venue"):
        if col not in df:
            df[col] = pd.NA
    return df[MATCH_COLUMNS]


def _load_brasileirao() -> pd.DataFrame:
    raw = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df = pd.DataFrame(
        {
            "date": raw["datetime"].map(parse_date),
            "season": raw["season"],
            "competition": COMP_BRASILEIRAO,
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            "round": raw["round"],
        }
    )
    return _finalize_matches(df, "Brasileirao_Matches")


def _load_copa_do_brasil() -> pd.DataFrame:
    raw = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    stage = raw["round"].map(lambda r: f"Round {r}" if pd.notna(r) else pd.NA)
    df = pd.DataFrame(
        {
            "date": raw["datetime"].map(parse_date),
            "season": raw["season"],
            "competition": COMP_COPA_DO_BRASIL,
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            "round": raw["round"],
            "stage": stage,
        }
    )
    return _finalize_matches(df, "Brazilian_Cup_Matches")


def _load_libertadores() -> pd.DataFrame:
    raw = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df = pd.DataFrame(
        {
            "date": raw["datetime"].map(parse_date),
            "season": raw["season"],
            "competition": COMP_LIBERTADORES,
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            "stage": raw["stage"],
        }
    )
    return _finalize_matches(df, "Libertadores_Matches")


def _load_br_football() -> pd.DataFrame:
    raw = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df = pd.DataFrame(
        {
            "date": raw["date"].map(parse_date),
            "season": raw["date"].map(lambda d: parse_date(d).year
                                      if pd.notna(parse_date(d)) else pd.NA),
            "competition": raw["tournament"].map(
                lambda t: _BR_TOURNAMENT_MAP.get(normalize_text(t), str(t))
            ),
            "home_team": raw["home"],
            "away_team": raw["away"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
        }
    )
    return _finalize_matches(df, "BR-Football-Dataset")


def _load_novo_brasileirao() -> pd.DataFrame:
    raw = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv")
    df = pd.DataFrame(
        {
            "date": raw["Data"].map(parse_date),
            "season": raw["Ano"],
            "competition": COMP_BRASILEIRAO,
            "home_team": raw["Equipe_mandante"],
            "away_team": raw["Equipe_visitante"],
            "home_goals": raw["Gols_mandante"],
            "away_goals": raw["Gols_visitante"],
            "round": raw["Rodada"],
            "venue": raw["Arena"],
        }
    )
    return _finalize_matches(df, "novo_campeonato_brasileiro")


def _load_players() -> pd.DataFrame:
    raw = pd.read_csv(DATA_DIR / "fifa_data.csv", low_memory=False)
    df = raw.rename(columns={"Jersey Number": "JerseyNumber"})
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["name_key"] = df["Name"].map(normalize_text)
    df["club_key"] = df["Club"].map(normalize_text)
    df["club_team_key"] = df["Club"].map(normalize_team)
    df["nationality_key"] = df["Nationality"].map(normalize_text)
    return df


@lru_cache(maxsize=1)
def get_store() -> SoccerStore:
    """Load (once) and return the shared :class:`SoccerStore`."""
    matches = pd.concat(
        [
            _load_brasileirao(),
            _load_copa_do_brasil(),
            _load_libertadores(),
            _load_br_football(),
            _load_novo_brasileirao(),
        ],
        ignore_index=True,
    )
    return SoccerStore(matches=matches, players=_load_players())
