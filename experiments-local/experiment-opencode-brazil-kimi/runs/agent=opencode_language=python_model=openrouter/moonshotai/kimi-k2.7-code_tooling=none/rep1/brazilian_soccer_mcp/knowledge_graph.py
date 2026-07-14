"""In-memory knowledge graph over the Brazilian soccer datasets."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

BR_STATES: Set[str] = {
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
}

PREFIXES: List[str] = sorted(
    [
        "sport club do recife",
        "sport club",
        "sociedade esportiva",
        "clube de regatas do",
        "clube de regatas",
        "esporte clube",
        "futebol clube",
        "clube",
        "esporte",
        "futebol",
        "sociedade",
        "sport",
        "associacao",
        "associacao desportiva",
        "atletica",
        "ec",
        "fc",
        "ac",
        "aa",
        "ad",
    ],
    key=len,
    reverse=True,
)

TRAILING_TOKENS: Set[str] = {"ec", "fc", "ac", "aa", "ad"}

# Normalized canonical keys for the biggest clubs.  Aliases are stored normalized.
CANONICAL: Dict[str, Dict[str, Any]] = {
    "flamengo": {
        "display": "Flamengo",
        "states": {"RJ"},
        "aliases": {"flamengo"},
    },
    "fluminense": {
        "display": "Fluminense",
        "states": {"RJ"},
        "aliases": {"fluminense"},
    },
    "palmeiras": {
        "display": "Palmeiras",
        "states": {"SP"},
        "aliases": {"palmeiras"},
    },
    "corinthians": {
        "display": "Corinthians",
        "states": {"SP"},
        "aliases": {"corinthians", "corinthians paulista", "sport club corinthians paulista"},
    },
    "sao-paulo": {
        "display": "São Paulo",
        "states": {"SP"},
        "aliases": {"sao paulo", "sao paulo fc"},
    },
    "santos": {
        "display": "Santos",
        "states": {"SP"},
        "aliases": {"santos"},
    },
    "vasco": {
        "display": "Vasco da Gama",
        "states": {"RJ"},
        "aliases": {"vasco", "vasco da gama"},
    },
    "gremio": {
        "display": "Grêmio",
        "states": {"RS"},
        "aliases": {"gremio"},
    },
    "atletico-mg": {
        "display": "Atlético-MG",
        "states": {"MG"},
        "aliases": {"atletico mineiro", "atletico mg", "atletico-mg"},
    },
    "atletico-go": {
        "display": "Atlético-GO",
        "states": {"GO"},
        "aliases": {"atletico goianiense", "atletico go", "atletico-go"},
    },
    "atletico-pr": {
        "display": "Athletico-PR",
        "states": {"PR"},
        "aliases": {
            "athletico",
            "athletico paranaense",
            "athletico pr",
            "athletico-pr",
            "atletico paranaense",
            "atletico pr",
            "atletico-pr",
        },
    },
    "cruzeiro": {
        "display": "Cruzeiro",
        "states": {"MG"},
        "aliases": {"cruzeiro"},
    },
    "botafogo": {
        "display": "Botafogo",
        "states": {"RJ"},
        "aliases": {"botafogo"},
    },
    "bahia": {
        "display": "Bahia",
        "states": {"BA"},
        "aliases": {"bahia", "esporte clube bahia"},
    },
    "internacional": {
        "display": "Internacional",
        "states": {"RS"},
        "aliases": {"internacional"},
    },
    "coritiba": {
        "display": "Coritiba",
        "states": {"PR"},
        "aliases": {"coritiba"},
    },
    "fortaleza": {
        "display": "Fortaleza",
        "states": {"CE"},
        "aliases": {"fortaleza"},
    },
    "ceara": {
        "display": "Ceará",
        "states": {"CE"},
        "aliases": {"ceara"},
    },
    "goias": {
        "display": "Goiás",
        "states": {"GO"},
        "aliases": {"goias"},
    },
    "avai": {
        "display": "Avaí",
        "states": {"SC"},
        "aliases": {"avai"},
    },
    "chapecoense": {
        "display": "Chapecoense",
        "states": {"SC"},
        "aliases": {"chapecoense"},
    },
    "sport": {
        "display": "Sport",
        "states": {"PE"},
        "aliases": {"sport", "sport club do recife"},
    },
    "ponte-preta": {
        "display": "Ponte Preta",
        "states": {"SP"},
        "aliases": {"ponte preta"},
    },
    "bragantino": {
        "display": "Red Bull Bragantino",
        "states": {"SP"},
        "aliases": {"bragantino", "red bull bragantino"},
    },
    "juventude": {
        "display": "Juventude",
        "states": {"RS"},
        "aliases": {"juventude"},
    },
    "america-mg": {
        "display": "América-MG",
        "states": {"MG"},
        "aliases": {"america mg", "america-mg", "america"},
    },
}

def normalize_text(text: Any) -> str:
    """Return a lower-case, accent-free, normalized string."""
    if pd.isna(text):
        return ""
    s = str(text).strip().lower()
    s = "".join(
        c
        for c in unicodedata.normalize("NFKD", s)
        if unicodedata.category(c) != "Mn"
    )
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def _remove_suffix_parenthetical(name: str) -> str:
    """Strip trailing parenthetical content such as '(URU)'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def extract_team(name: Any) -> tuple[str, Optional[str]]:
    """Extract base name and Brazilian state code from a team name."""
    raw = str(name).strip()
    raw = _remove_suffix_parenthetical(raw)
    match = re.search(r"(?:^|[\s\-])([A-Z]{2})$", raw)
    if match and match.group(1) in BR_STATES:
        state = match.group(1)
        base = raw[: match.start()].strip(" -")
        return base, state
    return raw, None


def clean_base(base: str) -> str:
    """Normalize and strip common leading/trailing club-type words."""
    nb = normalize_text(base)
    for prefix in PREFIXES:
        if nb.startswith(prefix + " "):
            nb = nb[len(prefix) + 1 :].strip()
    tokens = nb.split()
    while tokens and tokens[-1] in TRAILING_TOKENS:
        tokens.pop()
    return " ".join(tokens)


def get_canonical(name: Any) -> str:
    """Return a canonical team key for *name*."""
    base, state = extract_team(name)
    raw_norm = normalize_text(base)
    cleaned = clean_base(base)

    candidates = [cleaned, raw_norm]

    # Exact alias match (state aware).
    for candidate in candidates:
        for key, info in CANONICAL.items():
            if candidate in info["aliases"]:
                if state is None or state in info["states"]:
                    return key

    # State-based abbreviation disambiguation for Atlético clubs.
    if cleaned in ("atletico", "athletico"):
        if state == "PR":
            return "atletico-pr"
        if state == "MG":
            return "atletico-mg"
        if state == "GO":
            return "atletico-go"

    # Prefix alias match (state aware).
    for candidate in candidates:
        for key, info in CANONICAL.items():
            for alias in info["aliases"]:
                if candidate.startswith(alias + " "):
                    if state is None or state in info["states"]:
                        return key

    return cleaned


def _state_ok(query_key: str, team_state: Any) -> bool:
    """False when a known-club query is paired with a conflicting state suffix."""
    if team_state is None or pd.isna(team_state) or query_key not in CANONICAL:
        return True
    return team_state in CANONICAL[query_key]["states"]


def _key_match(team_key: str, team_state: Any, query_key: str) -> bool:
    """Check whether *team_key* matches *query_key*."""
    if not _state_ok(query_key, team_state):
        return False

    if team_key == query_key:
        return True

    if team_key.startswith(query_key + "-") or team_key.startswith(query_key + " "):
        return True

    if (" " + query_key + " ") in (" " + team_key + " "):
        return True

    return False


def team_matches(raw_name: Any, query_name: Any) -> bool:
    """Return True when *raw_name* should match the user-supplied *query_name*."""
    team_key = get_canonical(raw_name)
    _, team_state = extract_team(raw_name)
    query_key = get_canonical(query_name)
    return _key_match(team_key, team_state, query_key)


def display_name(name: Any) -> str:
    """Return a display-friendly team name."""
    canon = get_canonical(name)
    if canon in CANONICAL:
        return CANONICAL[canon]["display"]
    base, _ = extract_team(name)
    return base.strip() or str(name).strip()


# Pre-normalize aliases for performance.
for _key, _info in CANONICAL.items():
    _info["aliases"] = {normalize_text(a) for a in _info["aliases"]}


def normalize_competition(query: Optional[str]) -> Optional[List[str]]:
    """Map a free-form competition name to internal competition keys."""
    if not query:
        return None
    q = normalize_text(query)

    if "libertadores" in q:
        return ["Copa Libertadores"]

    if q in {"brasileirao", "serie a", "campeonato brasileiro"}:
        return ["Brasileirão"]
    if "serie b" in q:
        return ["Brasileirão Série B"]
    if "serie c" in q:
        return ["Brasileirão Série C"]
    if "brasileir" in q or "campeonato brasileiro" in q:
        return ["Brasileirão", "Brasileirão Série B", "Brasileirão Série C"]

    if "copa do brasil" in q or "brazilian cup" in q:
        return ["Copa do Brasil"]

    return None


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


class SoccerKnowledgeGraph:
    """Loads, normalizes and answers queries over the provided CSV datasets."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.matches = self._load_matches()
        self.players = self._load_players()

    def _load_matches(self) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []

        # 1. Brasileirão Serie A
        path = self.data_dir / "Brasileirao_Matches.csv"
        if path.exists():
            df = pd.read_csv(path)
            dt = pd.to_datetime(df["datetime"], errors="coerce")
            frames.append(
                pd.DataFrame(
                    {
                        "competition": "Brasileirão",
                        "season": _to_int(df["season"]),
                        "date": dt.dt.date,
                        "datetime": dt,
                        "home_team": df["home_team"].astype(str),
                        "away_team": df["away_team"].astype(str),
                        "home_goal": pd.to_numeric(df["home_goal"], errors="coerce"),
                        "away_goal": pd.to_numeric(df["away_goal"], errors="coerce"),
                        "round": _to_int(df["round"]),
                        "stage": pd.NA,
                        "stadium": pd.NA,
                        "source": "Brasileirao_Matches.csv",
                    }
                )
            )

        # 2. Copa do Brasil
        path = self.data_dir / "Brazilian_Cup_Matches.csv"
        if path.exists():
            df = pd.read_csv(path)
            dt = pd.to_datetime(df["datetime"], errors="coerce")
            frames.append(
                pd.DataFrame(
                    {
                        "competition": "Copa do Brasil",
                        "season": _to_int(df["season"]),
                        "date": dt.dt.date,
                        "datetime": dt,
                        "home_team": df["home_team"].astype(str),
                        "away_team": df["away_team"].astype(str),
                        "home_goal": pd.to_numeric(df["home_goal"], errors="coerce"),
                        "away_goal": pd.to_numeric(df["away_goal"], errors="coerce"),
                        "round": _to_int(df["round"]),
                        "stage": pd.NA,
                        "stadium": pd.NA,
                        "source": "Brazilian_Cup_Matches.csv",
                    }
                )
            )

        # 3. Copa Libertadores
        path = self.data_dir / "Libertadores_Matches.csv"
        if path.exists():
            df = pd.read_csv(path)
            dt = pd.to_datetime(df["datetime"], errors="coerce")
            frames.append(
                pd.DataFrame(
                    {
                        "competition": "Copa Libertadores",
                        "season": _to_int(df["season"]),
                        "date": dt.dt.date,
                        "datetime": dt,
                        "home_team": df["home_team"].astype(str),
                        "away_team": df["away_team"].astype(str),
                        "home_goal": pd.to_numeric(df["home_goal"], errors="coerce"),
                        "away_goal": pd.to_numeric(df["away_goal"], errors="coerce"),
                        "round": pd.NA,
                        "stage": df["stage"].astype(str).where(df["stage"].notna(), pd.NA),
                        "stadium": pd.NA,
                        "source": "Libertadores_Matches.csv",
                    }
                )
            )

        # 4. Extended BR-Football dataset
        path = self.data_dir / "BR-Football-Dataset.csv"
        if path.exists():
            df = pd.read_csv(path)
            dt = pd.to_datetime(df["date"], errors="coerce")
            comp_map = {
                "Serie A": "Brasileirão",
                "Serie B": "Brasileirão Série B",
                "Serie C": "Brasileirão Série C",
                "Copa do Brasil": "Copa do Brasil",
            }
            frames.append(
                pd.DataFrame(
                    {
                        "competition": df["tournament"].map(comp_map).fillna(df["tournament"]),
                        "season": _to_int(dt.dt.year),
                        "date": dt.dt.date,
                        "datetime": dt,
                        "home_team": df["home"].astype(str),
                        "away_team": df["away"].astype(str),
                        "home_goal": pd.to_numeric(df["home_goal"], errors="coerce"),
                        "away_goal": pd.to_numeric(df["away_goal"], errors="coerce"),
                        "round": pd.NA,
                        "stage": pd.NA,
                        "stadium": pd.NA,
                        "source": "BR-Football-Dataset.csv",
                    }
                )
            )

        # 5. Historical Brasileirão (2003-2019)
        path = self.data_dir / "novo_campeonato_brasileiro.csv"
        if path.exists():
            df = pd.read_csv(path)
            dt = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
            frames.append(
                pd.DataFrame(
                    {
                        "competition": "Brasileirão",
                        "season": _to_int(df["Ano"]),
                        "date": dt.dt.date,
                        "datetime": dt,
                        "home_team": df["Equipe_mandante"].astype(str),
                        "away_team": df["Equipe_visitante"].astype(str),
                        "home_goal": pd.to_numeric(df["Gols_mandante"], errors="coerce"),
                        "away_goal": pd.to_numeric(df["Gols_visitante"], errors="coerce"),
                        "round": _to_int(df["Rodada"]),
                        "stage": pd.NA,
                        "stadium": df["Arena"].astype(str).where(df["Arena"].notna(), pd.NA),
                        "source": "novo_campeonato_brasileiro.csv",
                    }
                )
            )

        matches = pd.concat(frames, ignore_index=True)

        # Derived canonical / display columns.
        matches["home_canonical"] = matches["home_team"].apply(get_canonical)
        matches["away_canonical"] = matches["away_team"].apply(get_canonical)
        matches["home_state"] = matches["home_team"].apply(lambda x: extract_team(x)[1])
        matches["away_state"] = matches["away_team"].apply(lambda x: extract_team(x)[1])
        matches["home_display"] = matches["home_team"].apply(display_name)
        matches["away_display"] = matches["away_team"].apply(display_name)

        # Goal difference for convenience.
        matches["goal_diff"] = matches["home_goal"] - matches["away_goal"]
        matches["total_goals"] = matches["home_goal"] + matches["away_goal"]

        # Deduplicate overlapping sources (e.g. Brasileirao_Matches and BR-Football
        # both contain Serie A fixtures).  Prefer the dedicated match files.
        source_priority = {
            "Brasileirao_Matches.csv": 1,
            "Brazilian_Cup_Matches.csv": 1,
            "Libertadores_Matches.csv": 1,
            "novo_campeonato_brasileiro.csv": 2,
            "BR-Football-Dataset.csv": 3,
        }
        matches["_priority"] = matches["source"].map(source_priority).fillna(99).astype(int)
        matches = matches.sort_values("_priority").drop_duplicates(
            subset=["competition", "season", "home_canonical", "away_canonical"],
            keep="first",
        )
        matches = matches.drop(columns=["_priority"])

        return matches

    def _load_players(self) -> pd.DataFrame:
        path = self.data_dir / "fifa_data.csv"
        if not path.exists():
            return pd.DataFrame()

        df = pd.read_csv(path, low_memory=False)
        keep = {
            "ID": "id",
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
        }
        df = df[[c for c in keep if c in df.columns]].rename(columns=keep)
        df["overall"] = pd.to_numeric(df["overall"], errors="coerce")
        df["potential"] = pd.to_numeric(df["potential"], errors="coerce")
        df["age"] = pd.to_numeric(df["age"], errors="coerce").astype("Int64")
        return df

    def _parse_date(self, value: Optional[str]) -> Optional[pd.Timestamp]:
        if not value:
            return None
        dt = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt

    def _filter_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> pd.DataFrame:
        df = self.matches.copy()

        if competition is not None:
            keys = normalize_competition(competition)
            if keys is not None:
                df = df[df["competition"].isin(keys)]

        if season is not None:
            df = df[df["season"].notna() & (df["season"] == season)]

        if from_date is not None:
            ts = self._parse_date(from_date)
            if ts is not None:
                d = ts.date()
                df = df[df["date"].notna() & (df["date"] >= d)]

        if to_date is not None:
            ts = self._parse_date(to_date)
            if ts is not None:
                d = ts.date()
                df = df[df["date"].notna() & (df["date"] <= d)]

        def home_matches(row: pd.Series, q: str) -> bool:
            return _key_match(row["home_canonical"], row["home_state"], get_canonical(q))

        def away_matches(row: pd.Series, q: str) -> bool:
            return _key_match(row["away_canonical"], row["away_state"], get_canonical(q))

        if team is not None:
            df = df[df.apply(lambda row: home_matches(row, team) or away_matches(row, team), axis=1)]

        if opponent is not None:
            if team is not None:
                df = df[
                    df.apply(
                        lambda row: (
                            home_matches(row, team) and away_matches(row, opponent)
                        )
                        or (
                            home_matches(row, opponent) and away_matches(row, team)
                        ),
                        axis=1,
                    )
                ]
            else:
                df = df[
                    df.apply(
                        lambda row: home_matches(row, opponent) or away_matches(row, opponent),
                        axis=1,
                    )
                ]

        return df

    def _format_match(self, row: pd.Series) -> str:
        parts = []
        if pd.notna(row["date"]):
            parts.append(str(row["date"]))

        def fmt_goal(value):
            return str(int(value)) if pd.notna(value) else "?"

        parts.append(
            f"{row['home_display']} {fmt_goal(row['home_goal'])}-"
            f"{fmt_goal(row['away_goal'])} {row['away_display']}"
        )
        detail = [row["competition"]]
        if pd.notna(row["round"]):
            detail.append(f"Round {int(row['round'])}")
        if pd.notna(row["stage"]):
            detail.append(str(row["stage"]))
        return f"- {' '.join(parts)} ({', '.join(detail)})"

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Return a formatted list of matches matching the criteria."""
        df = self._filter_matches(team, opponent, competition, season, from_date, to_date)
        df = df.sort_values("date", ascending=False)
        total = len(df)
        if total == 0:
            return "No matches found for the requested criteria."

        lines = [f"Found {total} match(es):"]
        for _, row in df.head(limit).iterrows():
            lines.append(self._format_match(row))
        if total > limit:
            lines.append(f"... ({total - limit} more)")
        return "\n".join(lines)

    def get_head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Return head-to-head results and a summary record."""
        df = self._filter_matches(None, None, competition, season, None, None)
        key_a = get_canonical(team_a)
        key_b = get_canonical(team_b)

        def both(row: pd.Series) -> bool:
            home_key = row["home_canonical"]
            away_key = row["away_canonical"]
            home_state = row["home_state"]
            away_state = row["away_state"]
            a_home = _key_match(home_key, home_state, key_a) and _key_match(away_key, away_state, key_b)
            b_home = _key_match(home_key, home_state, key_b) and _key_match(away_key, away_state, key_a)
            return a_home or b_home

        df = df[df.apply(both, axis=1)].sort_values("date", ascending=False)
        total = len(df)
        if total == 0:
            return f"No matches found between {display_name(team_a)} and {display_name(team_b)}."

        wins_a = draws = wins_b = 0
        for _, row in df.iterrows():
            a_is_home = _key_match(row["home_canonical"], row["home_state"], key_a)
            team_a_goals = row["home_goal"] if a_is_home else row["away_goal"]
            team_b_goals = row["away_goal"] if a_is_home else row["home_goal"]
            if team_a_goals > team_b_goals:
                wins_a += 1
            elif team_a_goals < team_b_goals:
                wins_b += 1
            else:
                draws += 1

        lines = [
            f"{display_name(team_a)} vs {display_name(team_b)}:",
            f"Head-to-head in dataset: {display_name(team_a)} {wins_a} wins, {display_name(team_b)} {wins_b} wins, {draws} draws",
            f"Recent matches ({min(limit, total)} of {total}):",
        ]
        for _, row in df.head(limit).iterrows():
            lines.append(self._format_match(row))
        if total > limit:
            lines.append(f"... ({total - limit} more)")
        return "\n".join(lines)

    def get_team_stats(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: Optional[str] = None,
    ) -> str:
        """Return win/loss/draw stats for a team."""
        key = get_canonical(team)
        df = self._filter_matches(None, None, competition, season, None, None)

        def team_rows(row: pd.Series) -> tuple[bool, bool]:
            is_home = _key_match(row["home_canonical"], row["home_state"], key)
            is_away = _key_match(row["away_canonical"], row["away_state"], key)
            return is_home, is_away

        records = []
        for _, row in df.iterrows():
            is_home, is_away = team_rows(row)
            if not is_home and not is_away:
                continue
            if venue == "home" and not is_home:
                continue
            if venue == "away" and not is_away:
                continue
            gf = row["home_goal"] if is_home else row["away_goal"]
            ga = row["away_goal"] if is_home else row["home_goal"]
            records.append({"gf": gf, "ga": ga})

        if not records:
            return f"No matches found for {display_name(team)} with the requested filters."

        df_stats = pd.DataFrame(records)
        wins = int((df_stats["gf"] > df_stats["ga"]).sum())
        draws = int((df_stats["gf"] == df_stats["ga"]).sum())
        losses = int((df_stats["gf"] < df_stats["ga"]).sum())
        gf = int(df_stats["gf"].sum())
        ga = int(df_stats["ga"].sum())
        win_rate = (wins / len(df_stats)) * 100 if len(df_stats) else 0.0

        venue_label = venue.title() if venue else "Overall"
        comp_label = f" {competition}" if competition else ""
        season_label = f" {season}" if season else ""
        lines = [
            f"{display_name(team)} {venue_label.lower()} record{comp_label}{season_label}:",
            f"- Matches: {len(df_stats)}",
            f"- Wins: {wins}, Draws: {draws}, Losses: {losses}",
            f"- Goals For: {gf}, Goals Against: {ga}",
            f"- Win rate: {win_rate:.1f}%",
        ]
        return "\n".join(lines)

    def get_competition_standings(
        self,
        competition: str,
        season: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Return a league table computed from match results."""
        df = self._filter_matches(None, None, competition, season, None, None)
        df = df[df["home_goal"].notna() & df["away_goal"].notna()]
        if df.empty:
            return "No matches available to compute standings."

        rows = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "team_key": row["home_canonical"],
                    "gf": row["home_goal"],
                    "ga": row["away_goal"],
                }
            )
            rows.append(
                {
                    "team_key": row["away_canonical"],
                    "gf": row["away_goal"],
                    "ga": row["home_goal"],
                }
            )
        stats = pd.DataFrame(rows)
        stats["win"] = stats["gf"] > stats["ga"]
        stats["draw"] = stats["gf"] == stats["ga"]
        stats["loss"] = stats["gf"] < stats["ga"]
        stats["points"] = stats["win"] * 3 + stats["draw"]

        grouped = (
            stats.groupby("team_key")
            .agg(
                points=("points", "sum"),
                wins=("win", "sum"),
                draws=("draw", "sum"),
                losses=("loss", "sum"),
                gf=("gf", "sum"),
                ga=("ga", "sum"),
                played=("points", "size"),
            )
            .reset_index()
        )
        grouped = grouped.sort_values(
            ["points", "wins", "gf"], ascending=[False, False, False]
        ).reset_index(drop=True)

        lines = [
            f"{competition}{' ' + str(season) if season else ''} Final Standings (calculated from matches):"
        ]
        for i, row in grouped.iterrows():
            display = CANONICAL.get(row["team_key"], {}).get("display", row["team_key"].title())
            pos = i + 1
            line = (
                f"{pos}. {display} - {int(row['points'])} pts "
                f"({int(row['wins'])}W, {int(row['draws'])}D, {int(row['losses'])}L)"
            )
            if pos == 1:
                line += " - Champion"
            lines.append(line)
            if limit and pos >= limit:
                remaining = len(grouped) - limit
                if remaining > 0:
                    lines.append(f"... ({remaining} more teams)")
                break
        return "\n".join(lines)

    def get_top_scoring_teams(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Return the teams with the most goals scored."""
        df = self._filter_matches(None, None, competition, season, None, None)
        df = df[df["home_goal"].notna() & df["away_goal"].notna()]
        if df.empty:
            return "No matches available."

        home = pd.DataFrame(
            {"team_key": df["home_canonical"], "goals": df["home_goal"]}
        )
        away = pd.DataFrame(
            {"team_key": df["away_canonical"], "goals": df["away_goal"]}
        )
        goals = pd.concat([home, away], ignore_index=True)
        grouped = (
            goals.groupby("team_key")["goals"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
            .head(limit)
        )

        lines = ["Top scoring teams:"]
        for i, row in grouped.iterrows():
            display = CANONICAL.get(row["team_key"], {}).get("display", row["team_key"].title())
            lines.append(f"{i + 1}. {display} - {int(row['goals'])} goals")
        return "\n".join(lines)

    def get_biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Return matches with the largest goal difference."""
        df = self._filter_matches(None, None, competition, season, None, None)
        df = df[df["home_goal"].notna() & df["away_goal"].notna()].copy()
        if df.empty:
            return "No matches available."
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        df = df.sort_values("margin", ascending=False).head(limit)

        lines = ["Biggest victories:"]
        for _, row in df.iterrows():
            lines.append(self._format_match(row))
        return "\n".join(lines)

    def get_average_goals(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Return average goals per match and home win rate."""
        df = self._filter_matches(None, None, competition, season, None, None)
        df = df[df["home_goal"].notna() & df["away_goal"].notna()]
        if df.empty:
            return "No matches available."

        avg = df["total_goals"].mean()
        home_wins = int((df["home_goal"] > df["away_goal"]).sum())
        home_win_rate = (home_wins / len(df)) * 100

        label_parts = []
        if competition:
            label_parts.append(competition)
        if season:
            label_parts.append(str(season))
        label = " ".join(label_parts) if label_parts else "All competitions"

        return (
            f"{label}:\n"
            f"- Average goals per match: {avg:.2f}\n"
            f"- Home win rate: {home_win_rate:.1f}%"
        )

    def list_competitions(self) -> str:
        comps = sorted(self.matches["competition"].dropna().unique().tolist())
        return "Available competitions:\n" + "\n".join(f"- {c}" for c in comps)

    def list_seasons(self, competition: Optional[str] = None) -> str:
        df = self.matches
        if competition is not None:
            keys = normalize_competition(competition)
            if keys is not None:
                df = df[df["competition"].isin(keys)]
        seasons = sorted(df["season"].dropna().unique().tolist())
        if not seasons:
            return "No seasons found."
        header = f" for {competition}" if competition else ""
        return f"Available seasons{header}:\n" + "\n".join(f"- {s}" for s in seasons)

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Search the FIFA player dataset."""
        df = self.players.copy()
        if df.empty:
            return "Player data is not available."

        if name:
            q = normalize_text(name)
            df = df[df["name"].fillna("").apply(lambda x: q in normalize_text(x))]
        if nationality:
            q = normalize_text(nationality)
            df = df[df["nationality"].fillna("").apply(lambda x: q in normalize_text(x))]
        if club:
            q = normalize_text(club)
            df = df[df["club"].fillna("").apply(lambda x: q in normalize_text(x))]
        if position:
            q = normalize_text(position)
            df = df[df["position"].fillna("").apply(lambda x: q in normalize_text(x))]
        if min_overall is not None:
            df = df[df["overall"] >= min_overall]

        df = df.sort_values("overall", ascending=False).head(limit)
        total = len(df)
        if total == 0:
            return "No players found for the requested criteria."

        lines = [f"Found {total} player(s):"]
        for _, row in df.iterrows():
            lines.append(
                f"- {row['name']} (Overall: {row['overall']}, Position: {row['position']}, "
                f"Club: {row['club']}, Nationality: {row['nationality']})"
            )
        return "\n".join(lines)


_knowledge_graph: Optional[SoccerKnowledgeGraph] = None


def get_knowledge_graph(data_dir: Optional[Path] = None) -> SoccerKnowledgeGraph:
    """Return a lazily-initialized knowledge graph."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = SoccerKnowledgeGraph(data_dir or DATA_DIR)
    return _knowledge_graph
