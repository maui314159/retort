"""Data loader and normalizer for the Brazilian Soccer MCP server."""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Common Brazilian state abbreviations used as suffixes in team names.
STATE_ABBREVS = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma",
    "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn",
    "rs", "ro", "rr", "sc", "sp", "se", "to",
}

# Map specific raw forms (accent-folded and lowercased) directly to a canonical
# name. This disambiguates clubs whose nickname is shared across states, e.g.
# Atlético-MG vs Athletico-PR, América-MG vs América-RN.
# Both dash and space-separated variants are included because the parser
# normalizes separators to spaces before lookup.
TEAM_ALIASES = {
    # Athletico / Atlético variations
    "athletico-pr": "atletico paranaense",
    "athletico pr": "atletico paranaense",
    "atletico-pr": "atletico paranaense",
    "atletico pr": "atletico paranaense",
    "athletico-pr": "atletico paranaense",
    "athletico pr": "atletico paranaense",
    "atletico paranaense": "atletico paranaense",
    "athletico paranaense": "atletico paranaense",
    "atletico-mg": "atletico mineiro",
    "atletico mg": "atletico mineiro",
    "athletico-mg": "atletico mineiro",
    "athletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "athletico mineiro": "atletico mineiro",
    "atletico-go": "atletico goianiense",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    "athletico-go": "atletico goianiense",
    "athletico go": "atletico goianiense",
    "athletico goianiense": "atletico goianiense",
    "clube atletico mineiro": "atletico mineiro",
    "clube atletico paranaense": "atletico paranaense",
    "sociedade esportiva palmeiras": "palmeiras",
    "sport club corinthians paulista": "corinthians",
    "sport club internacional": "internacional",
    "fluminense football club": "fluminense",
    "clube de regatas do flamengo": "flamengo",
    "clube de regatas vasco da gama": "vasco da gama",
    "botafogo de futebol e regatas": "botafogo",
    "esporte clube bahia": "bahia",
    "gremio foot ball porto alegrense": "gremio",
    "santos futebol clube": "santos",
    "sao paulo futebol clube": "sao paulo",
    "coritiba foot ball club": "coritiba",
    "goias esporte clube": "goias",
    # América / America variations
    "america-mg": "america mineiro",
    "america mg": "america mineiro",
    "america mineiro": "america mineiro",
    "america-rn": "america rn",
    "america rn": "america rn",
    "america fc natal": "america fc natal",
    "americano rj": "americano rj",
    # Vasco variations
    "vasco-rj": "vasco da gama",
    "vasco rj": "vasco da gama",
    "vasco da gama-rj": "vasco da gama",
    "vasco da gama rj": "vasco da gama",
    "vasco da gama": "vasco da gama",
    "vasco": "vasco da gama",
    # Sport variations
    "sport-pe": "sport recife",
    "sport pe": "sport recife",
    "sport recife": "sport recife",
    "sport club do recife": "sport recife",
    # Ceará
    "ceara-ce": "ceara",
    "ceara ce": "ceara",
    "ceara sporting club": "ceara",
    "ceara": "ceara",
    # Chapecoense
    "chapecoense-sc": "chapecoense",
    "chapecoense sc": "chapecoense",
    "chapecoense": "chapecoense",
    # Coritiba
    "coritiba-pr": "coritiba",
    "coritiba pr": "coritiba",
    "coritiba": "coritiba",
    # Bragantino
    "red bull bragantino-sp": "bragantino",
    "red bull bragantino sp": "bragantino",
    "red bull bragantino": "bragantino",
    "bragantino-sp": "bragantino",
    "bragantino sp": "bragantino",
    "bragantino": "bragantino",
    # Juventude
    "ec juventude": "juventude",
    "juventude-rs": "juventude",
    "juventude rs": "juventude",
    "juventude": "juventude",
    # Paraná
    "parana-pr": "parana",
    "parana pr": "parana",
    "parana": "parana",
    # Goiás
    "goias-go": "goias",
    "goias go": "goias",
    "goias": "goias",
    # Criciúma
    "criciuma-sc": "criciuma",
    "criciuma sc": "criciuma",
    "criciuma": "criciuma",
    # Avaí
    "avai-sc": "avai",
    "avai sc": "avai",
    "avai": "avai",
    # Figueirense
    "figueirense-sc": "figueirense",
    "figueirense sc": "figueirense",
    "figueirense": "figueirense",
    # Fortaleza
    "fortaleza-ce": "fortaleza",
    "fortaleza ce": "fortaleza",
    "fortaleza esporte clube": "fortaleza",
    "fortaleza": "fortaleza",
    "fortaleza fc": "fortaleza",
    # Cuiabá
    "cuiaba-mt": "cuiaba",
    "cuiaba mt": "cuiaba",
    "cuiaba": "cuiaba",
    # CSA
    "csa-al": "csa",
    "csa al": "csa",
    "csa": "csa",
    # Botafogo
    "botafogo-rj": "botafogo",
    "botafogo rj": "botafogo",
    "botafogo": "botafogo",
    # Flamengo / Fluminense
    "flamengo-rj": "flamengo",
    "flamengo rj": "flamengo",
    "flamengo": "flamengo",
    "fluminense-rj": "fluminense",
    "fluminense rj": "fluminense",
    "fluminense": "fluminense",
    # Santos / Palmeiras / São Paulo / Corinthians / Grêmio / Internacional
    "santos-sp": "santos",
    "santos sp": "santos",
    "santos": "santos",
    "palmeiras-sp": "palmeiras",
    "palmeiras sp": "palmeiras",
    "palmeiras": "palmeiras",
    "sao paulo-sp": "sao paulo",
    "sao paulo sp": "sao paulo",
    "sao paulo": "sao paulo",
    "corinthians-sp": "corinthians",
    "corinthians sp": "corinthians",
    "corinthians": "corinthians",
    "gremio-rs": "gremio",
    "gremio rs": "gremio",
    "gremio": "gremio",
    "internacional-rs": "internacional",
    "internacional rs": "internacional",
    "internacional": "internacional",
    "cruzeiro-mg": "cruzeiro",
    "cruzeiro mg": "cruzeiro",
    "cruzeiro": "cruzeiro",
    "bahia-ba": "bahia",
    "bahia ba": "bahia",
    "bahia": "bahia",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "vitoria-ba": "vitoria",
    "vitoria ba": "vitoria",
    "vitoria": "vitoria",
    "esporte clube vitoria": "vitoria",
}


def _remove_accents(value: str) -> str:
    """Remove accents from a string using NFKD normalization."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", value)
        if unicodedata.category(c) != "Mn"
    )


def normalize_team_name(name: str) -> str:
    """Return a normalized canonical team name for matching.

    The normalization handles:
    - explicit aliases for clubs with ambiguous short names (Athletico-PR,
      Atlético-MG, América-MG, Vasco, etc.)
    - stripping Brazilian state suffixes (e.g. ``Palmeiras-SP`` -> ``Palmeiras``)
    - removing leading/trailing whitespace
    - accent folding (e.g. ``São Paulo`` -> ``Sao Paulo``)
    - lowercasing
    - stripping noisy punctuation / suffix tokens
    - removing parenthetical notes
    """
    if not isinstance(name, str):
        name = str(name)

    # Strip parenthetical notes like "(antigo Esporte Clube Barreira)"
    name = re.sub(r"\s*\([^)]*\)", "", name)

    # Build a raw accent-folded / lowercased representation with the state
    # suffix still attached, so we can disambiguate e.g. Athletico-PR vs
    # Atletico-MG before dropping the state abbreviation.
    raw = _remove_accents(name).lower()
    raw = re.sub(r"[^a-z0-9\s]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw in TEAM_ALIASES:
        return TEAM_ALIASES[raw]

    # Split by common separators and drop state abbreviations from the end.
    parts = [p.strip() for p in re.split(r"[-/]", name) if p.strip()]
    while parts and parts[-1].lower() in STATE_ABBREVS:
        parts.pop()

    normalized = " ".join(parts)
    normalized = _remove_accents(normalized)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Final alias check in case a full-form name survives state stripping.
    if normalized in TEAM_ALIASES:
        return TEAM_ALIASES[normalized]

    return normalized


def team_matches(team_a: str, team_b: str) -> bool:
    """Return True if ``team_a`` matches ``team_b`` under normalization.

    Matching is symmetric and supports partial substrings, which is needed
    because one dataset may say ``Athletico-PR`` while another says
    ``Athletico Paranaense``.
    """
    a = normalize_team_name(team_a)
    b = normalize_team_name(team_b)
    if not a or not b:
        return False
    if a == b:
        return True
    # Allow one normalized name to be a whole-word subset of the other, e.g.
    # "corinthians" matches "sport club corinthians paulista".
    a_words = set(a.split())
    b_words = set(b.split())
    if len(a_words) == 1 or len(b_words) == 1:
        # Single-word query can match against any word in multi-word name.
        if a_words & b_words:
            return True
    return a in b or b in a


def _parse_datetime(value: str) -> Optional[datetime]:
    """Parse a datetime from several common formats."""
    if pd.isna(value):
        return None
    value = str(value).strip()
    if not value or value.lower() == "nan":
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # Fall back to pandas smart parsing.
    try:
        return pd.to_datetime(value)
    except Exception:
        return None


def _parse_date(value) -> Optional[pd.Timestamp]:
    """Parse a date value, returning a pandas Timestamp (UTC-naive)."""
    dt = _parse_datetime(value)
    if dt is None:
        return None
    return pd.Timestamp(dt.date())


def _safe_int(value, default: Optional[int] = None) -> Optional[int]:
    """Coerce a value to int, treating missing/invalid as default."""
    if pd.isna(value):
        return default
    try:
        return int(float(str(value).replace("-", "").strip() or 0))
    except (ValueError, TypeError):
        return default


class BrazilianSoccerData:
    """In-memory repository for Brazilian soccer datasets."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.matches: pd.DataFrame = pd.DataFrame()
        self.players: pd.DataFrame = pd.DataFrame()

    def load(self) -> None:
        """Load and normalize all provided CSV datasets."""
        self.matches = self._load_matches()
        self.players = self._load_players()

    def _load_matches(self) -> pd.DataFrame:
        matches = []

        # 1. Brasileirão Serie A
        bras = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv")
        bras["competition"] = "Brasileirão"
        bras["date"] = pd.to_datetime(bras["datetime"], errors="coerce")
        bras["season"] = bras["season"].astype("Int64")
        bras["round"] = bras["round"].astype("Int64")
        bras = bras.rename(columns={
            "home_team": "home_team_raw",
            "away_team": "away_team_raw",
            "home_goal": "home_goals",
            "away_goal": "away_goals",
        })
        bras["home_team"] = bras["home_team_raw"].apply(normalize_team_name)
        bras["away_team"] = bras["away_team_raw"].apply(normalize_team_name)
        bras["stage"] = None
        bras["stadium"] = None
        matches.append(bras[[
            "date", "home_team_raw", "away_team_raw", "home_team", "away_team",
            "home_goals", "away_goals", "season", "round", "stage",
            "competition", "stadium",
        ]])

        # 2. Copa do Brasil
        cup = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv")
        cup["competition"] = "Copa do Brasil"
        cup["date"] = pd.to_datetime(cup["datetime"], errors="coerce")
        cup["season"] = cup["season"].astype("Int64")
        cup["stage"] = cup["round"].astype(str)
        cup["round"] = cup["round"].astype("Int64")
        cup = cup.rename(columns={
            "home_team": "home_team_raw",
            "away_team": "away_team_raw",
            "home_goal": "home_goals",
            "away_goal": "away_goals",
        })
        cup["home_team"] = cup["home_team_raw"].apply(normalize_team_name)
        cup["away_team"] = cup["away_team_raw"].apply(normalize_team_name)
        cup["stadium"] = None
        matches.append(cup[[
            "date", "home_team_raw", "away_team_raw", "home_team", "away_team",
            "home_goals", "away_goals", "season", "round", "stage",
            "competition", "stadium",
        ]])

        # 3. Copa Libertadores
        lib = pd.read_csv(self.data_dir / "Libertadores_Matches.csv")
        lib["competition"] = "Copa Libertadores"
        lib["date"] = pd.to_datetime(lib["datetime"], errors="coerce")
        lib["season"] = pd.to_numeric(lib["season"], errors="coerce").astype("Int64")
        lib["home_goals"] = pd.to_numeric(lib["home_goal"], errors="coerce")
        lib["away_goals"] = pd.to_numeric(lib["away_goal"], errors="coerce")
        lib["round"] = None
        lib["stage"] = lib["stage"].astype(str)
        lib = lib.rename(columns={
            "home_team": "home_team_raw",
            "away_team": "away_team_raw",
        })
        lib["home_team"] = lib["home_team_raw"].apply(normalize_team_name)
        lib["away_team"] = lib["away_team_raw"].apply(normalize_team_name)
        lib["stadium"] = None
        matches.append(lib[[
            "date", "home_team_raw", "away_team_raw", "home_team", "away_team",
            "home_goals", "away_goals", "season", "round", "stage",
            "competition", "stadium",
        ]])

        # 4. Extended BR Football Dataset
        ext = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv")
        ext["competition"] = ext["tournament"].replace({
            "Serie A": "Brasileirão",
            "Serie B": "Brasileirão Série B",
            "Serie C": "Brasileirão Série C",
            "Copa do Brasil": "Copa do Brasil",
        })
        ext["date"] = pd.to_datetime(ext["date"], errors="coerce")
        ext["season"] = ext["date"].dt.year
        ext["round"] = None
        ext["stage"] = None
        ext = ext.rename(columns={
            "home": "home_team_raw",
            "away": "away_team_raw",
            "home_goal": "home_goals",
            "away_goal": "away_goals",
        })
        ext["home_team"] = ext["home_team_raw"].apply(normalize_team_name)
        ext["away_team"] = ext["away_team_raw"].apply(normalize_team_name)
        ext["stadium"] = None
        matches.append(ext[[
            "date", "home_team_raw", "away_team_raw", "home_team", "away_team",
            "home_goals", "away_goals", "season", "round", "stage",
            "competition", "stadium",
        ]])

        # 5. Historical Brasileirão (2003-2019)
        hist = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv")
        hist["competition"] = "Brasileirão"
        hist["date"] = hist["Data"].apply(lambda x: _parse_date(x))
        hist["season"] = hist["Ano"].astype("Int64")
        hist["round"] = hist["Rodada"].astype("Int64")
        hist["stage"] = None
        hist["home_goals"] = hist["Gols_mandante"]
        hist["away_goals"] = hist["Gols_visitante"]
        hist = hist.rename(columns={
            "Equipe_mandante": "home_team_raw",
            "Equipe_visitante": "away_team_raw",
            "Arena": "stadium",
        })
        hist["home_team"] = hist["home_team_raw"].apply(normalize_team_name)
        hist["away_team"] = hist["away_team_raw"].apply(normalize_team_name)
        matches.append(hist[[
            "date", "home_team_raw", "away_team_raw", "home_team", "away_team",
            "home_goals", "away_goals", "season", "round", "stage",
            "competition", "stadium",
        ]])

        all_matches = pd.concat(matches, ignore_index=True)
        all_matches["match_id"] = all_matches.index

        # Ensure numeric goal columns are floats for aggregation.
        all_matches["home_goals"] = pd.to_numeric(all_matches["home_goals"], errors="coerce")
        all_matches["away_goals"] = pd.to_numeric(all_matches["away_goals"], errors="coerce")

        # Deduplicate overlapping matches from multiple datasets.
        # Matches are loaded in priority order (official/competition-specific files
        # first, then the generic extended dataset), so ``keep='first'`` retains
        # the higher-quality source.
        # For league competitions, an ordered pair of teams appears only once per
        # season, so we deduplicate by competition/season/teams regardless of
        # small date differences across datasets. For cup competitions, we keep
        # the match date so multiple ties between the same teams are preserved.
        all_matches["dedup_date"] = pd.to_datetime(all_matches["date"], errors="coerce").dt.date
        is_league = all_matches["competition"].str.startswith("Brasileirão")
        all_matches["dedup_key"] = (
            all_matches["competition"].astype(str) + "|" +
            all_matches["season"].astype(str) + "|" +
            all_matches["home_team"].astype(str) + "|" +
            all_matches["away_team"].astype(str) + "|" +
            all_matches["dedup_date"].astype(str)
        )
        all_matches.loc[is_league, "dedup_key"] = (
            all_matches.loc[is_league, "competition"].astype(str) + "|" +
            all_matches.loc[is_league, "season"].astype(str) + "|" +
            all_matches.loc[is_league, "home_team"].astype(str) + "|" +
            all_matches.loc[is_league, "away_team"].astype(str)
        )
        # Prefer rows that have both goal values populated.
        all_matches["has_goals"] = all_matches["home_goals"].notna() & all_matches["away_goals"].notna()
        all_matches = all_matches.sort_values(
            by=["has_goals"], ascending=False
        ).drop_duplicates(subset=["dedup_key"], keep="first")
        all_matches = all_matches.drop(columns=["dedup_date", "dedup_key", "has_goals"])

        # Sort by date descending for recency queries.
        all_matches = all_matches.sort_values(by="date", ascending=False, ignore_index=True)
        return all_matches

    def _load_players(self) -> pd.DataFrame:
        players = pd.read_csv(self.data_dir / "fifa_data.csv")
        players = players.rename(columns={
            "Name": "name",
            "Age": "age",
            "Nationality": "nationality",
            "Overall": "overall",
            "Potential": "potential",
            "Club": "club",
            "Position": "position",
            "Jersey Number": "jersey_number",
            "Height": "height",
            "Weight": "weight",
        })
        players["name_norm"] = players["name"].fillna("").apply(normalize_team_name)
        return players

    def unique_teams(self) -> list:
        """Return a sorted list of unique canonical team names."""
        names = set(self.matches["home_team"].dropna()) | set(self.matches["away_team"].dropna())
        return sorted(name for name in names if name)


# Singleton accessor used by the MCP server.
_DATA: Optional[BrazilianSoccerData] = None


def get_data() -> BrazilianSoccerData:
    """Return the globally loaded data instance, loading on first call."""
    global _DATA
    if _DATA is None:
        _DATA = BrazilianSoccerData()
        _DATA.load()
    return _DATA


def reload_data() -> BrazilianSoccerData:
    """Force reload of data from disk."""
    global _DATA
    _DATA = BrazilianSoccerData()
    _DATA.load()
    return _DATA
