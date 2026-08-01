"""Data layer: loads the six Kaggle CSV files into a unified in-memory store.

The store exposes two main tables:

* ``matches`` — one row per match across every competition, with canonical
  team keys, parsed dates, normalized competition names and a ``source`` tag
  identifying the originating file. Cross-file duplicates (the same fixture
  appearing in more than one dataset) are collapsed.
* ``players`` — the FIFA player database with parsed numeric ratings.

Also builds a small knowledge-graph-style index: teams, competitions,
seasons and players are entity nodes linked by match/appearance relations.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .normalize import (
    DISPLAY_OVERRIDES,
    canonical_competition,
    canonical_team,
    normalize_text,
    parse_date,
)

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PACKAGE_ROOT / "data" / "kaggle"

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
BR_FOOTBALL_FILE = "BR-Football-Dataset.csv"
NOVO_BRASILEIRO_FILE = "novo_campeonato_brasileiro.csv"
FIFA_FILE = "fifa_data.csv"

MATCH_SOURCES = [
    BRASILEIRAO_FILE,
    CUP_FILE,
    LIBERTADORES_FILE,
    NOVO_BRASILEIRO_FILE,
    BR_FOOTBALL_FILE,
]

MATCH_COLUMNS = [
    "competition", "season", "date", "home", "away",
    "home_goals", "away_goals", "round", "stage", "source", "arena",
    "home_corners", "away_corners", "home_shots", "away_shots",
    "home_attacks", "away_attacks",
]

FIFA_KEEP_COLUMNS = {
    "ID": "id",
    "Name": "name",
    "Age": "age",
    "Nationality": "nationality",
    "Overall": "overall",
    "Potential": "potential",
    "Club": "club",
    "Position": "position",
    "Jersey Number": "jersey_number",
    "Preferred Foot": "preferred_foot",
    "Height": "height",
    "Weight": "weight",
    "Value": "value",
    "Wage": "wage",
    "Crossing": "crossing",
    "Finishing": "finishing",
    "HeadingAccuracy": "heading_accuracy",
    "ShortPassing": "short_passing",
    "Volleys": "volleys",
    "Dribbling": "dribbling",
    "Curve": "curve",
    "FKAccuracy": "fk_accuracy",
    "LongPassing": "long_passing",
    "BallControl": "ball_control",
    "Acceleration": "acceleration",
    "SprintSpeed": "sprint_speed",
    "Agility": "agility",
    "Reactions": "reactions",
    "Balance": "balance",
    "ShotPower": "shot_power",
    "Jumping": "jumping",
    "Stamina": "stamina",
    "Strength": "strength",
    "LongShots": "long_shots",
    "Aggression": "aggression",
    "Interceptions": "interceptions",
    "Positioning": "positioning",
    "Vision": "vision",
    "Penalties": "penalties",
    "Composure": "composure",
    "Marking": "marking",
    "StandingTackle": "standing_tackle",
    "SlidingTackle": "sliding_tackle",
    "GKDiving": "gk_diving",
    "GKHandling": "gk_handling",
    "GKKicking": "gk_kicking",
    "GKPositioning": "gk_positioning",
    "GKReflexes": "gk_reflexes",
}

POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "midfielder": {"CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM",
                   "LCM", "RCM", "LDM", "RDM"},
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
}

_POSITION_TO_GROUP = {
    pos: group for group, positions in POSITION_GROUPS.items() for pos in positions
}


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _read_csv(path: Path) -> pd.DataFrame:
    # utf-8-sig transparently handles the BOM present in fifa_data.csv.
    return pd.read_csv(path, encoding="utf-8-sig")


class DataStore:
    """In-memory knowledge store for Brazilian soccer data."""

    def __init__(self, data_dir: os.PathLike | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path(
            os.environ.get("SOCCER_DATA_DIR", DEFAULT_DATA_DIR)
        )
        self.source_row_counts: dict[str, int] = {}
        frames = [
            self._load_brasileirao(),
            self._load_cup(),
            self._load_libertadores(),
            self._load_novo_brasileiro(),
            self._load_br_football(),
        ]
        frames[-1] = self._drop_mislabeled_serie_a(frames[-1], frames[0], frames[3])
        matches = pd.concat(frames, ignore_index=True)
        self.matches = self._dedupe(matches)
        # The 2016 round-38 Chapecoense–Atlético-MG fixture was cancelled
        # after the LaMia Flight 2933 disaster and officially never played;
        # one source records a phantom 0-0 draw. Remove it.
        phantom = (
            (self.matches["competition"] == "serie a")
            & (self.matches["season"] == 2016)
            & (self.matches["home"] == "chapecoense")
            & (self.matches["away"] == "atletico mineiro")
        )
        self.matches = self.matches[~phantom].reset_index(drop=True)
        self.players = self._load_players()
        self._display_map = dict(DISPLAY_OVERRIDES)

    # ------------------------------------------------------------------
    # Loaders (one per file; each normalizes into the unified schema)
    # ------------------------------------------------------------------

    def _base_frame(self, df: pd.DataFrame, competition: str,
                    home_col: str, away_col: str, hg_col: str, ag_col: str,
                    season_col: str | None, date_col: str | None,
                    round_col: str | None, stage_col: str | None,
                    source: str, arena_col: str | None = None) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        out["competition"] = competition
        if season_col is not None:
            out["season"] = _to_int(df[season_col])
        else:
            out["season"] = pd.array([pd.NA] * len(df), dtype="Int64")
        if date_col is not None:
            out["date"] = df[date_col].map(parse_date)
        else:
            out["date"] = pd.NaT
        out["date"] = pd.to_datetime(out["date"])
        out["home"] = df[home_col].map(canonical_team)
        out["away"] = df[away_col].map(canonical_team)
        out["home_goals"] = _to_int(df[hg_col])
        out["away_goals"] = _to_int(df[ag_col])
        out["round"] = df[round_col].astype("string") if round_col else ""
        out["stage"] = df[stage_col].astype("string") if stage_col else ""
        out["source"] = source
        out["arena"] = df[arena_col].astype("string") if arena_col else ""
        for col in ("home_corners", "away_corners", "home_shots",
                    "away_shots", "home_attacks", "away_attacks"):
            out[col] = pd.array([pd.NA] * len(df), dtype="Float64")
        return out[MATCH_COLUMNS]

    def _load_brasileirao(self) -> pd.DataFrame:
        df = _read_csv(self.data_dir / BRASILEIRAO_FILE)
        self.source_row_counts[BRASILEIRAO_FILE] = len(df)
        return self._base_frame(
            df, "serie a", "home_team", "away_team",
            "home_goal", "away_goal", "season", "datetime",
            "round", None, BRASILEIRAO_FILE,
        )

    def _load_cup(self) -> pd.DataFrame:
        df = _read_csv(self.data_dir / CUP_FILE)
        self.source_row_counts[CUP_FILE] = len(df)
        frame = self._base_frame(
            df, "copa do brasil", "home_team", "away_team",
            "home_goal", "away_goal", "season", "datetime",
            "round", None, CUP_FILE,
        )
        # Cup rounds are numbered 1..N with N varying by season (e.g. the
        # 2012 final is round 6, the 2013 final is round 8), so label stages
        # relative to each season's final round.
        rounds = pd.to_numeric(frame["round"], errors="coerce")
        max_round = rounds.groupby(frame["season"]).transform("max")
        offset = max_round - rounds
        frame["stage"] = offset.map(_CUP_STAGE_BY_OFFSET).fillna("")
        frame.loc[rounds.isna(), "stage"] = ""
        return frame

    def _load_libertadores(self) -> pd.DataFrame:
        df = _read_csv(self.data_dir / LIBERTADORES_FILE)
        self.source_row_counts[LIBERTADORES_FILE] = len(df)
        return self._base_frame(
            df, "copa libertadores", "home_team", "away_team",
            "home_goal", "away_goal", "season", "datetime",
            None, "stage", LIBERTADORES_FILE,
        )

    def _load_novo_brasileiro(self) -> pd.DataFrame:
        df = _read_csv(self.data_dir / NOVO_BRASILEIRO_FILE)
        self.source_row_counts[NOVO_BRASILEIRO_FILE] = len(df)
        return self._base_frame(
            df, "serie a", "Equipe_mandante", "Equipe_visitante",
            "Gols_mandante", "Gols_visitante", "Ano", "Data",
            "Rodada", None, NOVO_BRASILEIRO_FILE, arena_col="Arena",
        )

    def _load_br_football(self) -> pd.DataFrame:
        df = _read_csv(self.data_dir / BR_FOOTBALL_FILE)
        self.source_row_counts[BR_FOOTBALL_FILE] = len(df)
        df = df.copy()
        df["competition_key"] = df["tournament"].map(canonical_competition)
        season_year = df["date"].str.slice(0, 4)
        # COVID-19 pushed the end of the 2020 seasons into early 2021
        # (Série A until 2021-02-25, Série B/C until late January, the
        # Copa do Brasil final until 2021-03-07), while the real 2021
        # seasons only started later (leagues in May, the cup on
        # 2021-03-09). Reassign the overflow rows to season 2020.
        overflow = (season_year == "2021") & (
            (df["date"] <= "2021-02-28")
            | ((df["competition_key"] == "copa do brasil")
               & (df["date"] <= "2021-03-08"))
        )
        season_year = season_year.mask(overflow, "2020")
        df["season"] = _to_int(season_year)
        out = pd.DataFrame()
        out["competition"] = df["competition_key"]
        out["season"] = df["season"]
        out["date"] = pd.to_datetime(df["date"].map(parse_date))
        out["home"] = df["home"].map(canonical_team)
        out["away"] = df["away"].map(canonical_team)
        out["home_goals"] = _to_int(df["home_goal"])
        out["away_goals"] = _to_int(df["away_goal"])
        out["round"] = ""
        out["stage"] = ""
        out["source"] = BR_FOOTBALL_FILE
        out["arena"] = ""
        out["home_corners"] = pd.to_numeric(df["home_corner"], errors="coerce")
        out["away_corners"] = pd.to_numeric(df["away_corner"], errors="coerce")
        out["home_shots"] = pd.to_numeric(df["home_shots"], errors="coerce")
        out["away_shots"] = pd.to_numeric(df["away_shots"], errors="coerce")
        out["home_attacks"] = pd.to_numeric(df["home_attack"], errors="coerce")
        out["away_attacks"] = pd.to_numeric(df["away_attack"], errors="coerce")
        out = out[out["competition"].notna()]
        return out[MATCH_COLUMNS]

    @staticmethod
    def _drop_mislabeled_serie_a(
        br_football: pd.DataFrame,
        brasileirao: pd.DataFrame,
        novo: pd.DataFrame,
    ) -> pd.DataFrame:
        """Drop BR-Football "Serie A" rows that cannot belong to the season.

        A few rows are mislabeled state-championship fixtures (e.g.
        Brasília FC vs CA Taguatinga, 2016-01-30). For seasons covered by
        the authoritative Série A files, the 20-team roster is known, so
        any BR-Football row involving an off-roster team is junk.
        """
        authoritative = pd.concat([brasileirao, novo], ignore_index=True)
        rosters: dict[int, set[str]] = {}
        for season, group in authoritative.groupby("season"):
            if pd.isna(season):
                continue
            rosters[int(season)] = set(group["home"]) | set(group["away"])
        keep = []
        for _, row in br_football.iterrows():
            if row["competition"] != "serie a" or pd.isna(row["season"]):
                keep.append(True)
                continue
            roster = rosters.get(int(row["season"]))
            keep.append(
                roster is None
                or (row["home"] in roster and row["away"] in roster)
            )
        return br_football[keep]

    def _load_players(self) -> pd.DataFrame:
        df = _read_csv(self.data_dir / FIFA_FILE)
        self.source_row_counts[FIFA_FILE] = len(df)
        keep = {src: dst for src, dst in FIFA_KEEP_COLUMNS.items() if src in df.columns}
        players = df[list(keep)].rename(columns=keep)
        for col in ("id", "age", "overall", "potential"):
            players[col] = _to_int(players[col])
        players["name_norm"] = players["name"].map(normalize_text)
        players["club_norm"] = players["club"].map(normalize_text)
        players["nationality_norm"] = players["nationality"].map(normalize_text)
        players["position_group"] = players["position"].map(_POSITION_TO_GROUP)
        return players

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    @staticmethod
    def _dedupe(matches: pd.DataFrame) -> pd.DataFrame:
        """Collapse the same fixture reported by multiple source files.

        A fixture is identified by competition, season and the canonical
        ordered team pair: in these datasets a pair meets at most once per
        competition-season with the same home/away arrangement, and keying
        on the date is unreliable (sources disagree by ±1 day for late
        kick-offs). When sources disagree on the score, the row from the
        earliest-loaded (most authoritative) source wins — rows are
        concatenated in ``MATCH_SOURCES`` priority order.
        """
        df = matches.copy()
        # astype("string").fillna("") — plain astype(str) keeps pd.NA on
        # Int64 columns, which would poison the concatenated key.
        df["_fixture"] = (
            df["competition"].astype("string").fillna("")
            + "|" + df["season"].astype("string").fillna("")
            + "|" + df["home"].astype("string").fillna("")
            + "|" + df["away"].astype("string").fillna("")
        )
        # Stable sort puts rows with a final score first inside each
        # fixture group (source priority is otherwise preserved), so a
        # played copy always beats a scheduled/scoreless placeholder.
        df["_scoreless"] = df["home_goals"].isna().astype(int)
        df = df.sort_values("_scoreless", kind="stable")
        df = df.drop_duplicates(subset="_fixture", keep="first")
        # Drop any remaining scoreless rows whose fixture exists played
        # elsewhere; keep genuinely unplayed matches (e.g. the 2015
        # Boca–River Libertadores tie abandoned at half-time).
        played_fixtures = set(df.loc[df["home_goals"].notna(), "_fixture"])
        superseded = df["home_goals"].isna() & df["_fixture"].isin(played_fixtures)
        df = df[~superseded]
        df = df.drop(columns=["_fixture", "_scoreless"])
        return df.sort_values(["date", "competition"], na_position="last").reset_index(drop=True)

    def display_team(self, key: str) -> str:
        """Human-friendly team name for a canonical key."""
        if key in self._display_map:
            return self._display_map[key]
        return key.title() if key else key

    # ------------------------------------------------------------------
    # Knowledge-graph-style conveniences
    # ------------------------------------------------------------------

    @property
    def teams(self) -> list[str]:
        return sorted(set(self.matches["home"]) | set(self.matches["away"]))

    @property
    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique())

    def seasons(self, competition: str | None = None) -> list[int]:
        df = self.matches
        if competition is not None:
            df = df[df["competition"] == competition]
        return sorted(int(s) for s in df["season"].dropna().unique())


_CUP_STAGE_BY_OFFSET = {
    0.0: "final",
    1.0: "semifinals",
    2.0: "quarterfinals",
    3.0: "round of 16",
    4.0: "third round",
    5.0: "second round",
    6.0: "first round",
}


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    """Process-wide cached :class:`DataStore` instance."""
    return DataStore()
