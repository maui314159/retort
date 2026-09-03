"""An in-memory knowledge graph over the Brazilian soccer datasets.

Nodes
-----
* :class:`Team`        - a club, keyed by the normalized team key.
* :class:`Player`      - a FIFA player record.
* :class:`Match`       - a single match (date, scores, competition, season).
* :class:`Competition` - a competition label aggregated across datasets.

Edges
-----
* ``Team -[:PLAYED_AS {side}]-> Match``        every match participation.
* ``Match -[:BELONGS_TO]-> Competition``       every match's competition.
* ``Player -[:MEMBER_OF]-> Team(club)``        current club affiliation.

The graph is materialized lazily on first access and cached for the lifetime
of the process. It deliberately uses an in-process store rather than an
external database so the benchmark runs without provisioning a Neo4j instance;
every operation is backed by the :mod:`brsl.data_loader` pandas DataFrames.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable

import pandas as pd

from . import data_loader as dl
from .normalization import normalize_team, team_matches


@dataclass(frozen=True)
class Team:
    key: str
    display: str
    states: frozenset[str]
    competitions: frozenset[str]

    def __str__(self) -> str:
        return self.display


@dataclass(frozen=True)
class Match:
    index: int
    date: pd.Timestamp
    home_team: str
    away_team: str
    home_team_key: str
    away_team_key: str
    home_goal: int
    away_goal: int
    competition: str
    season: int
    round: str | None
    stage: str | None
    stadium: str | None
    winner: str | None  # "home" | "away" | "draw" | None

    @property
    def home_win(self) -> bool:
        return self.winner == "home"

    @property
    def away_win(self) -> bool:
        return self.winner == "away"

    @property
    def draw(self) -> bool:
        return self.winner == "draw"


@dataclass(frozen=True)
class Competition:
    name: str
    match_count: int
    seasons: frozenset[int]


@dataclass
class KnowledgeGraph:
    """The in-memory graph over all loaded datasets."""

    matches_df: pd.DataFrame
    players_df: pd.DataFrame
    teams: dict[str, Team] = field(default_factory=dict)
    competitions: dict[str, Competition] = field(default_factory=dict)
    _match_records: list[Match] = field(default_factory=list)

    # ----- construction -------------------------------------------------
    @classmethod
    @lru_cache(maxsize=1)
    def load(cls) -> "KnowledgeGraph":
        matches = dl.load_matches()
        players = dl.load_players()
        graph = cls(matches_df=matches, players_df=players)
        graph._build()
        return graph

    def _build(self) -> None:
        df = self.matches_df
        teams: dict[str, Team] = {}
        comps: dict[str, set[int]] = {}
        for side in ("home", "away"):
            for _, row in df.iterrows():
                key = row[f"{side}_team_key"]
                if not key:
                    continue
                t = teams.setdefault(
                    key,
                    Team(key=key, display=row[f"{side}_team"],
                         states=frozenset(), competitions=frozenset()),
                )
                # accumulate states/competitions into a fresh frozen instance
                states = set(t.states)
                if row.get(f"{side}_state"):
                    states.add(row[f"{side}_state"])
                comps_for_team = set(t.competitions)
                comps_for_team.add(row["competition"])
                teams[key] = Team(
                    key=key, display=t.display,
                    states=frozenset(states),
                    competitions=frozenset(comps_for_team),
                )
                comps.setdefault(row["competition"], set()).add(
                    int(row["season"]) if pd.notna(row["season"]) else None
                )
        self.teams = teams

        self.competitions = {
            name: Competition(
                name=name,
                match_count=int((df["competition"] == name).sum()),
                seasons=frozenset(s for s in seasons if s is not None),
            )
            for name, seasons in comps.items()
        }

        records: list[Match] = []
        for i, row in df.iterrows():
            records.append(
                Match(
                    index=int(i),
                    date=row["date"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    home_team_key=row["home_team_key"],
                    away_team_key=row["away_team_key"],
                    home_goal=int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
                    away_goal=int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
                    competition=row["competition"],
                    season=int(row["season"]) if pd.notna(row["season"]) else None,
                    round=(None if pd.isna(row["round"]) else str(row["round"])),
                    stage=(None if pd.isna(row["stage"]) else str(row["stage"])),
                    stadium=(None if pd.isna(row["stadium"]) else str(row["stadium"])),
                    winner=(None if pd.isna(row["winner"]) else str(row["winner"])),
                )
            )
        self._match_records = records

    # ----- lookups ------------------------------------------------------
    def matches(self) -> list[Match]:
        return list(self._match_records)

    def find_teams(self, query: str) -> list[Team]:
        """Return all teams whose canonical name matches ``query``.

        A query may be a full name, a name with a state suffix, or an accented
        variant; see :func:`brsl.normalization.team_matches`.
        """
        if not query:
            return list(self.teams.values())
        norm = normalize_team(query)
        results: list[Team] = []
        seen: set[str] = set()
        for key, team in self.teams.items():
            if norm.key and norm.key == key:
                results.append(team)
                seen.add(key)
                continue
            if team_matches(query, team.display) or team_matches(query, key):
                if key not in seen:
                    results.append(team)
                    seen.add(key)
        return results

    def find_team(self, query: str) -> Team | None:
        teams = self.find_teams(query)
        if not teams:
            return None
        # Prefer an exact key match when several variants collide.
        norm = normalize_team(query)
        for t in teams:
            if t.key == norm.key:
                return t
        return teams[0]

    def matches_for_team(self, team_key: str) -> list[Match]:
        return [
            m for m in self._match_records
            if m.home_team_key == team_key or m.away_team_key == team_key
        ]

    def matches_between(self, team_a_key: str, team_b_key: str) -> list[Match]:
        return [
            m for m in self._match_records
            if {m.home_team_key, m.away_team_key} == {team_a_key, team_b_key}
        ]

    def players(self) -> pd.DataFrame:
        return self.players_df

    def find_player(self, name: str) -> pd.DataFrame:
        df = self.players_df
        if "Name" not in df.columns:
            return df.iloc[0:0]
        mask = df["Name"].astype(str).str.contains(name, case=False, na=False,
                                                   regex=False)
        return df[mask]

    def competitions_by_name(self, query: str) -> list[Competition]:
        from .query_engine import normalize_competition_query

        target = normalize_competition_query(query)
        if target is None:
            return list(self.competitions.values())
        mapping = {
            "Brasileirao Serie A": "brasileirao",
            "Brasileirao Serie A (2003-2019)": "brasileirao",
            "Serie A": "brasileirao",
            "Serie B": "serie_b",
            "Serie C": "serie_c",
            "Copa do Brasil": "copa_do_brasil",
            "Copa Libertadores": "libertadores",
        }
        out: list[Competition] = []
        seen: set[str] = set()
        for name, comp in self.competitions.items():
            if mapping.get(name) == target or name == query:
                if name not in seen:
                    out.append(comp)
                    seen.add(name)
        return out


def iter_team_names(df: pd.DataFrame) -> Iterable[str]:
    yield from df["home_team"].dropna().unique()
    yield from df["away_team"].dropna().unique()
