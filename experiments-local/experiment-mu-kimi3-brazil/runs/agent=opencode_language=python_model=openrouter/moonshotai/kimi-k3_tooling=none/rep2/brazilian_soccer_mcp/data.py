"""Data loading layer.

Loads the six Kaggle CSV files from ``data/kaggle/`` into a unified,
deduplicated match table plus a player table.  All team names are normalized
to canonical keys (see :mod:`.normalization`) and all dates to
``datetime.date`` objects, so every downstream query works on one consistent
schema regardless of the source file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .normalization import (
    COMP_BRASILEIRAO_A,
    COMP_BRASILEIRAO_B,
    COMP_BRASILEIRAO_C,
    COMP_COPA_DO_BRASIL,
    COMP_LIBERTADORES,
    norm_text,
    parse_date,
    team_key,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Priority used when the same match appears in more than one source file:
# lower number wins.
_SOURCE_PRIORITY = {
    "brasileirao_matches": 0,
    "brazilian_cup_matches": 1,
    "libertadores_matches": 2,
    "novo_campeonato_brasileiro": 3,
    "br_football_dataset": 4,
}

MATCH_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_key",
    "away_key",
    "home_goals",
    "away_goals",
    "competition",
    "season",
    "round",
    "source",
]


def _to_int(value: object) -> int | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


class DataStore:
    """In-memory store with the unified match table and the player table."""

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.matches = pd.DataFrame(columns=MATCH_COLUMNS)
        self.players = pd.DataFrame()
        self._display_names: dict[str, str] = {}
        self._graph = None
        self._canonical: pd.DataFrame | None = None
        self.load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        frames = [
            self._load_brasileirao(),
            self._load_copa_do_brasil(),
            self._load_libertadores(),
            self._load_novo_campeonato(),
            self._load_br_football(),
        ]
        matches = pd.concat(frames, ignore_index=True)
        matches = matches[matches["home_key"] != ""]
        matches = matches[matches["away_key"] != ""]
        # Deduplicate cross-source duplicates, keeping the highest-priority
        # source for each (date, fixture, competition) tuple.
        matches["_prio"] = matches["source"].map(_SOURCE_PRIORITY)
        matches = matches.sort_values("_prio")
        matches = matches.drop_duplicates(
            subset=["date", "home_key", "away_key", "competition"], keep="first"
        )
        matches = matches.drop(columns="_prio").reset_index(drop=True)
        # Normalize nullable numeric columns: plain Python ints, NaN -> None.
        # (pd.array(..., dtype=object): .map()/list assignment would make
        # pandas re-infer float64 and turn None back into NaN.)
        for col in ("home_goals", "away_goals", "season"):
            matches[col] = pd.array(
                [None if v is None or pd.isna(v) else int(v)
                 for v in matches[col].tolist()],
                dtype=object,
            )
        self.matches = matches
        self._build_display_names()
        self.players = self._load_players()

    def _records(self, df: pd.DataFrame, mapping: dict[str, str],
                 competition: str, source: str) -> pd.DataFrame:
        out = pd.DataFrame()
        out["date"] = df[mapping["date"]].map(parse_date)
        out["home_team"] = df[mapping["home"]].astype(str).str.strip()
        out["away_team"] = df[mapping["away"]].astype(str).str.strip()
        out["home_key"] = out["home_team"].map(team_key)
        out["away_key"] = out["away_team"].map(team_key)
        # object dtype keeps None (unplayed / unknown) instead of NaN coercion.
        out["home_goals"] = df[mapping["home_goals"]].map(_to_int).astype(object)
        out["away_goals"] = df[mapping["away_goals"]].map(_to_int).astype(object)
        out["competition"] = competition
        out["season"] = (
            df[mapping["season"]].map(_to_int).astype(object)
            if mapping.get("season") else None
        )
        out["round"] = (
            df[mapping["round"]].astype(str) if mapping.get("round") else ""
        )
        out["source"] = source
        return out[MATCH_COLUMNS]

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv")
        return self._records(
            df,
            {"date": "datetime", "home": "home_team", "away": "away_team",
             "home_goals": "home_goal", "away_goals": "away_goal",
             "season": "season", "round": "round"},
            COMP_BRASILEIRAO_A,
            "brasileirao_matches",
        )

    def _load_copa_do_brasil(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv")
        return self._records(
            df,
            {"date": "datetime", "home": "home_team", "away": "away_team",
             "home_goals": "home_goal", "away_goals": "away_goal",
             "season": "season", "round": "round"},
            COMP_COPA_DO_BRASIL,
            "brazilian_cup_matches",
        )

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Libertadores_Matches.csv")
        recs = self._records(
            df,
            {"date": "datetime", "home": "home_team", "away": "away_team",
             "home_goals": "home_goal", "away_goals": "away_goal",
             "season": "season", "round": "stage"},
            COMP_LIBERTADORES,
            "libertadores_matches",
        )
        # Rows without a season: infer the year from the match date.
        missing = recs["season"].isna()
        recs.loc[missing, "season"] = recs.loc[missing, "date"].map(
            lambda d: d.year if d else None
        )
        return recs

    def _load_novo_campeonato(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv")
        return self._records(
            df,
            {"date": "Data", "home": "Equipe_mandante",
             "away": "Equipe_visitante", "home_goals": "Gols_mandante",
             "away_goals": "Gols_visitante", "season": "Ano",
             "round": "Rodada"},
            COMP_BRASILEIRAO_A,
            "novo_campeonato_brasileiro",
        )

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv")
        comp_map = {
            "Serie A": COMP_BRASILEIRAO_A,
            "Serie B": COMP_BRASILEIRAO_B,
            "Serie C": COMP_BRASILEIRAO_C,
            "Copa do Brasil": COMP_COPA_DO_BRASIL,
        }
        df = df[df["tournament"].isin(comp_map)]
        recs = self._records(
            df,
            {"date": "date", "home": "home", "away": "away",
             "home_goals": "home_goal", "away_goals": "away_goal",
             "season": None, "round": None},
            COMP_BRASILEIRAO_A,  # placeholder, replaced below
            "br_football_dataset",
        )
        recs["competition"] = df["tournament"].map(comp_map).values
        recs["season"] = recs["date"].map(lambda d: d.year if d else None)
        return recs

    def _load_players(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "fifa_data.csv", low_memory=False)
        df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]
        df["_name_key"] = df["Name"].map(norm_text)
        df["_club_key"] = df["Club"].map(norm_text)
        df["_nat_key"] = df["Nationality"].map(norm_text)
        df["_pos_key"] = df["Position"].map(norm_text)
        return df

    # ------------------------------------------------------------------
    # Display names
    # ------------------------------------------------------------------

    def _build_display_names(self) -> None:
        """Pick the most common raw spelling as display name per team key."""
        counts: dict[str, dict[str, int]] = {}
        for raw, key in pd.concat(
            [self.matches[["home_team", "home_key"]].rename(
                columns={"home_team": "raw", "home_key": "key"}),
             self.matches[["away_team", "away_key"]].rename(
                columns={"away_team": "raw", "away_key": "key"})]
        ).itertuples(index=False):
            counts.setdefault(key, {})
            counts[key][raw] = counts[key].get(raw, 0) + 1
        self._display_names = {
            key: max(variants.items(), key=lambda kv: kv[1])[0]
            for key, variants in counts.items()
        }

    def display_name(self, key: str) -> str:
        """Human-friendly display name for a canonical team key."""
        if key in self._display_names:
            return self._display_names[key]
        return key.title()

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def team_keys(self) -> list[str]:
        keys = set(self.matches["home_key"]) | set(self.matches["away_key"])
        return sorted(keys)

    @property
    def canonical(self) -> pd.DataFrame:
        """One row per real-world match.

        Several source files cover the same competition/season (e.g. the 2019
        Brasileirão appears in three of them) with slightly different dates or
        team spellings, so exact-key deduplication cannot remove every
        duplicate.  For aggregate correctness we pick, per
        (competition, season), the single source with the most *played*
        matches (ties broken by source priority) and drop the rest.
        """
        if self._canonical is None:
            played = self.matches[
                self.matches["home_goals"].notna()
                & self.matches["away_goals"].notna()
                & self.matches["season"].notna()
            ]
            counts = (
                played.groupby(["competition", "season", "source"])
                .size()
                .reset_index(name="n")
            )
            best: dict[tuple[str, int], str] = {}
            for (comp, season), grp in counts.groupby(["competition", "season"]):
                ranked = sorted(
                    grp.itertuples(index=False),
                    key=lambda r: (-r.n, _SOURCE_PRIORITY[r.source]),
                )
                best[(comp, season)] = ranked[0].source
            keys = pd.Series(
                list(zip(self.matches["competition"], self.matches["season"])),
                index=self.matches.index,
            )
            chosen = keys.map(lambda k: best.get(k))
            mask = [
                c is None or c == s
                for c, s in zip(chosen.tolist(), self.matches["source"].tolist())
            ]
            self._canonical = self.matches[mask].reset_index(drop=True)
        return self._canonical

    @property
    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].unique())

    @property
    def graph(self):
        """Lazily-built knowledge graph over the loaded data."""
        if self._graph is None:
            from .graph import KnowledgeGraph

            self._graph = KnowledgeGraph(self)
        return self._graph

    def overview(self) -> dict:
        """Row counts and coverage per source file."""
        per_source = (
            self.matches.groupby("source")
            .agg(matches=("date", "size"),
                 first_season=("season", "min"),
                 last_season=("season", "max"))
            .reset_index()
            .to_dict("records")
        )
        return {
            "total_matches": int(len(self.matches)),
            "total_players": int(len(self.players)),
            "teams": len(self.team_keys),
            "competitions": self.competitions,
            "sources": per_source,
        }
