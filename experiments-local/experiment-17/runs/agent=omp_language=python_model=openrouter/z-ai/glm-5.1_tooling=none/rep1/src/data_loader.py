"""Data loader for Brazilian soccer datasets.

Normalizes team names, parses dates, and provides unified access
to all six CSV files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# ── Team name normalization ──────────────────────────────────────────

_STRIP_STATE_RE = re.compile(r"[-–]\s*[A-Z]{2}$")
_STRIP_PARENS_RE = re.compile(r"\s*\(.*?\)\s*$")
_STRIP_SUFFIX_RE = re.compile(
    r"\s+(Futebol Clube|Clube de Regatas|Sport Club|Esporte Clube|"
    r"Clube Atlético|Atlético Clube|Associação|Sociedade Esportiva|"
    r"Grupo Sportivo|Sport Club Recife e Esportes)$",
    re.IGNORECASE,
)

_KNOWN_ALIASES: dict[str, str] = {
    "corinthians": "Corinthians",
    "são paulo": "São Paulo",
    "sao paulo": "São Paulo",
    "palmeiras": "Palmeiras",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "santos": "Santos",
    "grêmio": "Grêmio",
    "gremio": "Grêmio",
    "cruzeiro": "Cruzeiro",
    "atlético-mg": "Atlético Mineiro",
    "atlético mineiro": "Atlético Mineiro",
    "atletico-mg": "Atlético Mineiro",
    "atletico mineiro": "Atlético Mineiro",
    "botafogo": "Botafogo",
    "internacional": "Internacional",
    "coritiba": "Coritiba",
    "bahia": "Bahia",
    "fortaleza": "Fortaleza",
    "athletico-pr": "Athletico Paranaense",
    "athletico paranaense": "Athletico Paranaense",
    "atletico-pr": "Athletico Paranaense",
    "atletico paranaense": "Athletico Paranaense",
    "bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
    "goiás": "Goiás",
    "goias": "Goiás",
    "américa-mg": "América Mineiro",
    "américa mineiro": "América Mineiro",
    "america-mg": "América Mineiro",
    "america mineiro": "América Mineiro",
    "ceará": "Ceará",
    "ceara": "Ceará",
    "sport": "Sport Recife",
    "sport recife": "Sport Recife",
    "chapecoense": "Chapecoense",
    "avaí": "Avaí",
    "avai": "Avaí",
    "paraná": "Paraná",
    "parana": "Paraná",
    "csa": "CSA",
    "cuiabá": "Cuiabá",
    "cuiaba": "Cuiabá",
    "juventude": "Juventude",
    "portuguesa": "Portuguesa",
    "náutico": "Náutico",
    "nautico": "Náutico",
    "ponte preta": "Ponte Preta",
    "figueirense": "Figueirense",
    "vitória": "Vitória",
    "vitoria": "Vitória",
    "criciúma": "Criciúma",
    "crisciuma": "Criciúma",
    "santa cruz": "Santa Cruz",
    "joinville": "Joinville",
    "ipatinga": "Ipatinga",
    "brasiliense": "Brasiliense",
    "paysandu": "Paysandu",
    "são caetano": "São Caetano",
    "sao caetano": "São Caetano",
}


def normalize_team(name: str) -> str:
    """Strip state suffixes, parentheticals, and map to canonical name."""
    if not isinstance(name, str) or not name.strip():
        return name
    s = name.strip()
    # Remove parenthetical notes like "(antigo Esporte Clube Barreira)"
    s = _STRIP_PARENS_RE.sub("", s)
    # Remove state suffix like "-RJ" or " - MG"
    s = _STRIP_STATE_RE.sub("", s).strip()
    # Remove common suffixes
    s = _STRIP_SUFFIX_RE.sub("", s).strip()
    # Alias lookup (case-insensitive, accent-insensitive)
    key = s.lower()
    if key in _KNOWN_ALIASES:
        return _KNOWN_ALIASES[key]
    # Title-case fallback
    return s


# ── Date parsing ────────────────────────────────────────────────────

def _parse_date(series: pd.Series) -> pd.Series:
    """Parse dates from multiple formats into datetime."""
    return pd.to_datetime(series, format="mixed", dayfirst=True, errors="coerce")


# ── Data loading ────────────────────────────────────────────────────

class SoccerData:
    """Lazy-loaded, normalized access to all Brazilian soccer datasets."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._dir = Path(data_dir) if data_dir else DATA_DIR
        self._brasileirao: pd.DataFrame | None = None
        self._cup: pd.DataFrame | None = None
        self._libertadores: pd.DataFrame | None = None
        self._extended: pd.DataFrame | None = None
        self._historical: pd.DataFrame | None = None
        self._players: pd.DataFrame | None = None

    # ── Properties (lazy load) ──────────────────────────────────────

    @property
    def brasileirao(self) -> pd.DataFrame:
        if self._brasileirao is None:
            df = pd.read_csv(self._dir / "Brasileirao_Matches.csv")
            df["home_team"] = df["home_team"].apply(normalize_team)
            df["away_team"] = df["away_team"].apply(normalize_team)
            df["date"] = _parse_date(df["datetime"])
            df["competition"] = "Brasileirão"
            self._brasileirao = df
        return self._brasileirao

    @property
    def cup(self) -> pd.DataFrame:
        if self._cup is None:
            df = pd.read_csv(self._dir / "Brazilian_Cup_Matches.csv")
            df["home_team"] = df["home_team"].apply(normalize_team)
            df["away_team"] = df["away_team"].apply(normalize_team)
            df["date"] = _parse_date(df["datetime"])
            df["competition"] = "Copa do Brasil"
            self._cup = df
        return self._cup

    @property
    def libertadores(self) -> pd.DataFrame:
        if self._libertadores is None:
            df = pd.read_csv(self._dir / "Libertadores_Matches.csv")
            df["home_team"] = df["home_team"].apply(normalize_team)
            df["away_team"] = df["away_team"].apply(normalize_team)
            df["date"] = _parse_date(df["datetime"])
            df["competition"] = "Copa Libertadores"
            # Coerce goals to numeric (CSV stores them as strings)
            df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
            df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
            self._libertadores = df
        return self._libertadores

    @property
    def extended(self) -> pd.DataFrame:
        if self._extended is None:
            df = pd.read_csv(self._dir / "BR-Football-Dataset.csv")
            df.rename(columns={"home": "home_team", "away": "away_team"}, inplace=True)
            df["home_team"] = df["home_team"].apply(normalize_team)
            df["away_team"] = df["away_team"].apply(normalize_team)
            df["date"] = _parse_date(df["date"])
            df["season"] = df["date"].dt.year
            self._extended = df
        return self._extended

    @property
    def historical(self) -> pd.DataFrame:
        if self._historical is None:
            df = pd.read_csv(self._dir / "novo_campeonato_brasileiro.csv")
            df.rename(
                columns={
                    "Data": "date_raw",
                    "Ano": "season",
                    "Rodada": "round",
                    "Equipe_mandante": "home_team",
                    "Equipe_visitante": "away_team",
                    "Gols_mandante": "home_goal",
                    "Gols_visitante": "away_goal",
                    "Vencedor": "winner",
                    "Arena": "stadium",
                },
                inplace=True,
            )
            df["home_team"] = df["home_team"].apply(normalize_team)
            df["away_team"] = df["away_team"].apply(normalize_team)
            df["date"] = _parse_date(df["date_raw"])
            df["competition"] = "Brasileirão (Historical)"
            self._historical = df
        return self._historical

    @property
    def players(self) -> pd.DataFrame:
        if self._players is None:
            df = pd.read_csv(self._dir / "fifa_data.csv", encoding="utf-8-sig")
            # Drop the unnamed first column
            df.drop(columns=[df.columns[0]], errors="ignore", inplace=True)
            df["Club"] = df["Club"].fillna("")
            df["Nationality"] = df["Nationality"].fillna("")
            self._players = df
        return self._players

    # ── Unified match views ─────────────────────────────────────────

    def all_matches(self) -> pd.DataFrame:
        """Return all match data with a unified schema."""
        frames = []
        for src in (self.brasileirao, self.cup, self.libertadores, self.historical):
            sub = src[["home_team", "away_team", "home_goal", "away_goal", "date", "season", "competition"]].copy()
            frames.append(sub)
        # Extended matches
        ext = self.extended[["home_team", "away_team", "home_goal", "away_goal", "date", "season", "tournament"]].copy()
        ext.rename(columns={"tournament": "competition"}, inplace=True)
        frames.append(ext)
        df = pd.concat(frames, ignore_index=True)
        # Ensure goal columns are numeric (some CSVs have string goals)
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    # ── Query helpers ───────────────────────────────────────────────

    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> pd.DataFrame:
        """Find matches matching the given criteria."""
        df = self.all_matches()
        team = normalize_team(team) if team else None
        opponent = normalize_team(opponent) if opponent else None

        if team:
            if home_only:
                df = df[df["home_team"] == team]
            elif away_only:
                df = df[df["away_team"] == team]
            else:
                df = df[(df["home_team"] == team) | (df["away_team"] == team)]

        if opponent:
            df = df[
                ((df["home_team"] == opponent) | (df["away_team"] == opponent))
            ]

        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]

        if season is not None:
            df = df[df["season"] == season]

        if date_from:
            df = df[df["date"] >= pd.Timestamp(date_from)]
        if date_to:
            df = df[df["date"] <= pd.Timestamp(date_to)]

        return df.sort_values("date", ascending=False)

    def head_to_head(self, team_a: str, team_b: str) -> dict:
        """Compute head-to-head record between two teams."""
        a = normalize_team(team_a)
        b = normalize_team(team_b)
        df = self.all_matches()
        matches = df[
            ((df["home_team"] == a) & (df["away_team"] == b))
            | ((df["home_team"] == b) & (df["away_team"] == a))
        ].copy()
        a_wins = 0
        b_wins = 0
        draws = 0
        for _, row in matches.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            if hg > ag:
                if row["home_team"] == a:
                    a_wins += 1
                else:
                    b_wins += 1
            elif hg < ag:
                if row["home_team"] == b:
                    b_wins += 1
                else:
                    a_wins += 1
            else:
                draws += 1
        return {
            "team_a": a,
            "team_b": b,
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "total_matches": len(matches),
            "matches": matches,
        }

    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
    ) -> dict:
        """Calculate win/draw/loss record and goals for a team."""
        team = normalize_team(team)
        df = self.all_matches()
        home = df[df["home_team"] == team]
        away = df[df["away_team"] == team]
        all_team = pd.concat([home, away])

        if season is not None:
            all_team = all_team[all_team["season"] == season]
        if competition:
            all_team = all_team[all_team["competition"].str.contains(competition, case=False, na=False)]

        wins = draws = losses = 0
        gf = ga = 0
        for _, row in all_team.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            is_home = row["home_team"] == team
            team_goals = int(hg if is_home else ag)
            opp_goals = int(ag if is_home else hg)
            gf += team_goals
            ga += opp_goals
            if team_goals > opp_goals:
                wins += 1
            elif team_goals < opp_goals:
                losses += 1
            else:
                draws += 1

        total = wins + draws + losses
        return {
            "team": team,
            "season": season,
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "win_rate": round(wins / total * 100, 1) if total else 0.0,
        }

    def standings(self, season: int, competition: str = "Brasileirão") -> list[dict]:
        """Calculate league standings from match results."""
        df = self.all_matches()
        df = df[
            (df["season"] == season)
            & df["competition"].str.contains(competition, case=False, na=False)
        ]
        teams: dict[str, dict] = {}
        for _, row in df.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            ht = row["home_team"]
            at = row["away_team"]
            for t in (ht, at):
                if t not in teams:
                    teams[t] = {"team": t, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
            teams[ht]["gf"] += int(hg)
            teams[ht]["ga"] += int(ag)
            teams[at]["gf"] += int(ag)
            teams[at]["ga"] += int(hg)
            if hg > ag:
                teams[ht]["w"] += 1
                teams[ht]["pts"] += 3
                teams[at]["l"] += 1
            elif hg < ag:
                teams[at]["w"] += 1
                teams[at]["pts"] += 3
                teams[ht]["l"] += 1
            else:
                teams[ht]["d"] += 1
                teams[at]["d"] += 1
                teams[ht]["pts"] += 1
                teams[at]["pts"] += 1

        table = sorted(teams.values(), key=lambda x: (-x["pts"], -(x["gf"] - x["ga"]), -x["gf"]))
        return table

    def biggest_wins(self, limit: int = 10, competition: str | None = None) -> list[dict]:
        """Find the largest goal-difference victories."""
        df = self.all_matches()
        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
        df = df.dropna(subset=["home_goal", "away_goal"])
        df = df.copy()
        df["diff"] = (df["home_goal"] - df["away_goal"]).abs()
        df = df.sort_values("diff", ascending=False).head(limit)
        results = []
        for _, row in df.iterrows():
            if row["home_goal"] > row["away_goal"]:
                winner, loser, wg, lg = row["home_team"], row["away_team"], row["home_goal"], row["away_goal"]
            else:
                winner, loser, wg, lg = row["away_team"], row["home_team"], row["away_goal"], row["home_goal"]
            results.append({
                "date": str(row["date"].date()) if pd.notna(row["date"]) else "unknown",
                "winner": winner,
                "loser": loser,
                "winner_goals": int(wg),
                "loser_goals": int(lg),
                "competition": row["competition"],
            })
        return results

    def avg_goals(self, competition: str | None = None) -> dict:
        """Calculate average goals per match."""
        df = self.all_matches()
        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
        df = df.dropna(subset=["home_goal", "away_goal"])
        total_goals = (df["home_goal"] + df["away_goal"]).sum()
        total_matches = len(df)
        home_wins = (df["home_goal"] > df["away_goal"]).sum()
        away_wins = (df["home_goal"] < df["away_goal"]).sum()
        draws = (df["home_goal"] == df["away_goal"]).sum()
        return {
            "total_matches": total_matches,
            "total_goals": int(total_goals),
            "avg_goals_per_match": round(total_goals / total_matches, 2) if total_matches else 0,
            "home_wins": int(home_wins),
            "away_wins": int(away_wins),
            "draws": int(draws),
            "home_win_rate": round(home_wins / total_matches * 100, 1) if total_matches else 0,
        }

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Search FIFA player data."""
        df = self.players
        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
        if club:
            df = df[df["Club"].str.contains(club, case=False, na=False)]
        if position:
            df = df[df["Position"].str.contains(position, case=False, na=False)]
        if min_overall is not None:
            df = df[df["Overall"] >= min_overall]
        df = df.sort_values("Overall", ascending=False)
        return df.head(limit)

    def brazilian_players_by_club(self) -> dict[str, dict]:
        """Group Brazilian players by club."""
        df = self.players[self.players["Nationality"] == "Brazil"]
        result = {}
        for club, group in df.groupby("Club"):
            if not club:
                continue
            result[club] = {
                "count": len(group),
                "avg_rating": round(group["Overall"].mean(), 1),
                "top_players": group.nlargest(3, "Overall")[["Name", "Overall", "Position"]].to_dict("records"),
            }
        return result
