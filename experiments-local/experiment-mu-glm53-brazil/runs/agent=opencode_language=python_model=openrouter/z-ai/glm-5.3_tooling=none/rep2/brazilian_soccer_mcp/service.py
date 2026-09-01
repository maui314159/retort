"""Query service joining matches, players and teams into answers.

:class:`SoccerDataService` loads every dataset once, normalizes team names
through :class:`~brazilian_soccer_mcp.normalize.TeamRegistry`, and exposes
the query methods that back the MCP tools: match search, head-to-head,
team statistics, standings, derbies, aggregated league statistics, and
player queries.

Because three of the match files overlap (the same Brasileirão and Copa do
Brasil fixtures appear in more than one dataset, often with slightly
different dates), the service resolves one *preferred source* per
(competition, season) pair before answering queries.  This keeps every
fixture exactly once in query results while still allowing explicit
source overrides for the extended-statistics dataset.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from .loaders import (
    SOURCE_LABELS,
    load_all,
)
from .models import Match, Player, TeamRecord
from .normalize import (
    TeamRegistry,
    norm_text,
    parse_date,
    parse_int,
    strip_accents,
)

COMPETITIONS: dict[str, str] = {
    "brasileirao-serie-a": "Brasileirão Série A",
    "brasileirao-serie-b": "Brasileirão Série B",
    "brasileirao-serie-c": "Brasileirão Série C",
    "copa-do-brasil": "Copa do Brasil",
    "copa-libertadores": "Copa Libertadores",
}

LEAGUE_COMPETITIONS = {
    "brasileirao-serie-a", "brasileirao-serie-b", "brasileirao-serie-c",
}

DOMESTIC_COMPETITIONS = {
    "brasileirao-serie-a", "brasileirao-serie-b", "brasileirao-serie-c",
    "copa-do-brasil",
}

DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo-rj", "fluminense-rj"),
    ("Clássico dos Milhões", "flamengo-rj", "vasco da gama"),
    ("Clássico Vovô", "vasco da gama", "botafogo-rj"),
    ("Gre-Nal", "gremio", "internacional-rs"),
    ("Clássico Mineiro", "atletico-mg", "cruzeiro"),
    ("Majestoso", "corinthians", "sao paulo"),
    ("Choque-Rei", "palmeiras", "sao paulo"),
    ("Derby Paulista", "corinthians", "palmeiras"),
    ("Ba-Vi", "bahia-ba", "vitoria-ba"),
    ("Clássico-Rei", "ceara", "fortaleza"),
    ("Clássico dos Clássicos", "sport", "nautico-pe"),
    ("Clássico Paranaense", "atletico-pr", "coritiba"),
]

POSITION_GROUPS = {
    "goalkeeper": ["GK"],
    "goleiro": ["GK"],
    "defender": ["CB", "LB", "RB", "LWB", "RWB"],
    "zagueiro": ["CB", "LB", "RB", "LWB", "RWB"],
    "midfielder": ["CDM", "CM", "CAM", "LM", "RM"],
    "meia": ["CDM", "CM", "CAM", "LM", "RM"],
    "forward": ["ST", "CF", "LW", "RW"],
    "attacker": ["ST", "CF", "LW", "RW"],
    "striker": ["ST", "CF"],
    "atacante": ["ST", "CF", "LW", "RW"],
}

POSITION_CODES = {
    "GK", "CB", "LB", "RB", "LWB", "RWB", "CDM", "CM", "CAM", "LM", "RM",
    "ST", "CF", "LW", "RW",
}

_DEFAULT_LIMIT = 30


def preferred_sources(comp_key: str, season: int | None) -> set[str] | None:
    """Return the source ids preferred for a (competition, season) pair."""
    if comp_key == "brasileirao-serie-a":
        if season is None:
            return None
        if 2012 <= season <= 2022:
            return {"brasileirao_matches"}
        if 2003 <= season <= 2011:
            return {"campeonato_2003_2019"}
        if season >= 2023:
            return {"br_football_stats"}
    elif comp_key == "copa-do-brasil":
        if season is None:
            return None
        if 2012 <= season <= 2021:
            return {"copa_do_brasil_matches"}
        return {"br_football_stats"}
    elif comp_key in ("brasileirao-serie-b", "brasileirao-serie-c"):
        return {"br_football_stats"}
    elif comp_key == "copa-libertadores":
        return {"libertadores_matches"}
    return None


class SoccerDataService:
    """In-memory query engine over the Brazilian soccer datasets."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data" / "kaggle"
        self.data_dir = Path(data_dir)
        self.registry = TeamRegistry()
        self.matches: list[Match] = []
        self.players: list[Player] = []

        raw_matches, raw_players = load_all(self.data_dir)
        for raw in raw_matches:
            self.registry.observe(raw.home_display, raw.home_uf)
            self.registry.observe(raw.away_display, raw.away_uf)
        self.registry.finalize()

        for raw in raw_matches:
            self.matches.append(self._build_match(raw))
        for raw in raw_players:
            self.players.append(Player(
                id=raw.id,
                name=raw.name,
                age=raw.age,
                nationality=raw.nationality,
                overall=raw.overall,
                potential=raw.potential,
                club=raw.club,
                club_key=self.registry.canonical(raw.club) if raw.club else "",
                position=raw.position,
                jersey_number=raw.jersey_number,
                height=raw.height,
                weight=raw.weight,
                preferred_foot=raw.preferred_foot,
                value=raw.value,
                wage=raw.wage,
            ))

        self._buckets: dict[tuple[str, int | None], list[Match]] = defaultdict(list)
        for match in self.matches:
            self._buckets[(match.competition_key, match.season)].append(match)
        self._resolved_buckets: dict[tuple[str, int | None], list[Match]] = {}
        for bucket_key, matches in self._buckets.items():
            sources = preferred_sources(bucket_key[0], bucket_key[1])
            if sources is None:
                self._resolved_buckets[bucket_key] = matches
            else:
                self._resolved_buckets[bucket_key] = [
                    m for m in matches if m.source in sources
                ]
        self._resolved_matches = [
            m for matches in self._resolved_buckets.values() for m in matches
        ]
        self._by_team: dict[str, list[Match]] = defaultdict(list)
        for match in self._resolved_matches:
            self._by_team[match.home_key].append(match)
            self._by_team[match.away_key].append(match)
        self._brazilian_team_keys = {
            match.home_key
            for match in self._resolved_matches
            if match.competition_key in DOMESTIC_COMPETITIONS
        } | {
            match.away_key
            for match in self._resolved_matches
            if match.competition_key in DOMESTIC_COMPETITIONS
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_match(self, raw) -> Match:
        home_key = self.registry.canonical(raw.home_display, raw.home_uf)
        away_key = self.registry.canonical(raw.away_display, raw.away_uf)
        return Match(
            date=raw.date,
            home=self.registry.display(home_key),
            away=self.registry.display(away_key),
            home_key=home_key,
            away_key=away_key,
            home_goals=raw.home_goals,
            away_goals=raw.away_goals,
            competition=raw.competition,
            competition_key=raw.competition_key,
            season=raw.season,
            source=raw.source,
            round_label=raw.round_label,
            stage=raw.stage,
            venue=raw.venue,
            time=raw.time,
            home_corners=raw.stats.get("home_corners"),
            away_corners=raw.stats.get("away_corners"),
            home_shots=raw.stats.get("home_shots"),
            away_shots=raw.stats.get("away_shots"),
            home_attacks=raw.stats.get("home_attacks"),
            away_attacks=raw.stats.get("away_attacks"),
            halftime_result=raw.stats.get("halftime_result"),
        )

    def _pool(
        self,
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
    ) -> list[Match]:
        comp_key = self._resolve_competition_key(competition) if competition else None
        if source:
            pool = self.matches
            if comp_key:
                pool = [m for m in pool if m.competition_key == comp_key]
            if season is not None:
                pool = [m for m in pool if m.season == season]
            return [m for m in pool if m.source == source]
        if comp_key is None and season is None:
            return self._resolved_matches
        if comp_key is not None and season is not None:
            return self._resolved_buckets.get((comp_key, season), [])
        if comp_key is not None:
            return [
                m for m in self._resolved_matches if m.competition_key == comp_key
            ]
        return [m for m in self._resolved_matches if m.season == season]

    def _resolve_competition_key(self, query: str) -> str | None:
        if not query:
            return None
        normalized = norm_text(query)
        for key, display in COMPETITIONS.items():
            if normalized in (norm_text(key), norm_text(display)):
                return key
        for key, display in COMPETITIONS.items():
            if normalized in norm_text(key) or normalized in norm_text(display):
                return key
        for key, display in COMPETITIONS.items():
            if norm_text(key) in normalized or norm_text(display) in normalized:
                return key
        return None

    def _resolve_competition_name(self, query: str) -> str | None:
        key = self._resolve_competition_key(query)
        return COMPETITIONS.get(key) if key else None

    def _sort_matches(self, matches: list[Match]) -> list[Match]:
        return sorted(matches, key=lambda m: (m.date is None, m.date or date.min))

    def _resolve_or_error(self, team: str) -> tuple[str | None, dict]:
        resolution = self.registry.resolve(team)
        if not resolution.found:
            payload = {
                "error": f"Team '{team}' not found in the dataset",
                "query": team,
            }
            if resolution.suggestions:
                payload["suggestions"] = resolution.suggestions
            else:
                payload["hint"] = "Try another spelling or use list_teams to browse."
            return None, payload
        return resolution.key, {"resolution": self._resolution_dict(resolution)}

    @staticmethod
    def _resolution_dict(resolution) -> dict:
        payload = {
            "key": resolution.key,
            "display": resolution.display,
            "matched_by": resolution.matched_by,
        }
        if resolution.alternatives:
            payload["alternatives"] = resolution.alternatives
        return payload

    @staticmethod
    def _as_date(value) -> date | None:
        if value is None or isinstance(value, date):
            return value
        return parse_date(value)

    def _match_finals(self, comp_key: str, season: int | None) -> set[int]:
        """Return ids of final matches for cup competitions."""
        finals: set[int] = set()
        seasons = [season] if season is not None else sorted({
            m.season for m in self.matches
            if m.competition_key == comp_key and m.season is not None
        })
        for season_value in seasons:
            bucket = self._pool(comp_key, season_value)
            rounds: dict[int, list[Match]] = defaultdict(list)
            for match in bucket:
                number = parse_int(match.round_label.split()[-1]) if match.round_label else None
                if number is not None:
                    rounds[number].append(match)
            if not rounds:
                continue
            max_round = max(rounds)
            if len(rounds[max_round]) <= 2:
                finals.update(id(m) for m in rounds[max_round])
        return finals

    def _stage_filter(self, matches: list[Match], stage: str) -> list[Match]:
        stage_norm = norm_text(stage)
        if stage_norm == "final":
            result = []
            for comp_key in {m.competition_key for m in matches}:
                comp_matches = [m for m in matches if m.competition_key == comp_key]
                if comp_key == "copa-do-brasil":
                    finals = self._match_finals(comp_key, None)
                    result.extend(m for m in comp_matches if id(m) in finals)
                else:
                    result.extend(
                        m for m in comp_matches
                        if m.stage and norm_text(m.stage) == "final"
                    )
            return result
        round_number = parse_int(stage)
        filtered = []
        for match in matches:
            labels = [match.stage or "", match.round_label or ""]
            if any(stage_norm and stage_norm in norm_text(label) for label in labels):
                filtered.append(match)
            elif round_number is not None and match.round_label:
                if parse_int(match.round_label.split()[-1]) == round_number:
                    filtered.append(match)
        return filtered

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------
    def resolve_team(self, name: str) -> dict:
        """Resolve a team name, reporting canonical key and alternatives."""
        resolution = self.registry.resolve(name)
        payload = {"query": name, "found": resolution.found}
        payload.update(self._resolution_dict(resolution))
        if not resolution.found and resolution.suggestions:
            payload["suggestions"] = resolution.suggestions
        return payload

    def list_teams(
        self,
        query: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 50,
    ) -> dict:
        """List known teams, optionally filtered by name or competition."""
        pool = self._pool(competition, season) if competition or season else None
        if pool is not None:
            keys = {m.home_key for m in pool} | {m.away_key for m in pool}
        else:
            keys = set(self.registry.keys())
        if query:
            needle = norm_text(query)
            keys = {key for key in keys if needle in norm_text(key)}
        teams = sorted(
            ({"key": key, "display": self.registry.display(key),
              "matches": self.registry.match_count(key)} for key in keys),
            key=lambda team: (-team["matches"], team["key"]),
        )
        return {
            "teams": teams[:limit],
            "total": len(teams),
            "truncated": len(teams) > limit,
        }

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------
    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from=None,
        date_to=None,
        stage: str | None = None,
        source: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict:
        """Search matches by team, opponent, competition, season or dates."""
        payload: dict = {"filters": {
            "team": team, "opponent": opponent, "competition": competition,
            "season": season, "stage": stage, "source": source,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        }}
        team_key = None
        if team:
            team_key, error = self._resolve_or_error(team)
            if team_key is None:
                return error
            payload["team"] = self._resolution_dict(self.registry.resolve(team))
        opponent_key = None
        if opponent:
            opponent_key, error = self._resolve_or_error(opponent)
            if opponent_key is None:
                return error
            payload["opponent"] = self._resolution_dict(
                self.registry.resolve(opponent)
            )
        comp_key = None
        if competition:
            comp_key = self._resolve_competition_key(competition)
            if comp_key is None:
                return {"error": f"Unknown competition '{competition}'",
                        "known_competitions": list(COMPETITIONS.values())}
            payload["competition"] = COMPETITIONS[comp_key]

        if source:
            pool = self.matches
            if comp_key:
                pool = [m for m in pool if m.competition_key == comp_key]
            if season is not None:
                pool = [m for m in pool if m.season == season]
            pool = [m for m in pool if m.source == source]
        else:
            pool = self._pool(competition, season)
        if team_key:
            pool = [m for m in pool if m.involves(team_key)]
        if opponent_key:
            if team_key:
                pool = [m for m in pool
                        if m.involves_pair(team_key, opponent_key)]
            else:
                pool = [m for m in pool if m.involves(opponent_key)]
        date_from_parsed = self._as_date(date_from)
        date_to_parsed = self._as_date(date_to)
        if date_from_parsed:
            pool = [m for m in pool if m.date and m.date >= date_from_parsed]
        if date_to_parsed:
            pool = [m for m in pool if m.date and m.date <= date_to_parsed]
        if stage:
            pool = self._stage_filter(pool, stage)

        ordered = self._sort_matches(pool)
        payload["total"] = len(ordered)
        payload["truncated"] = len(ordered) > limit
        payload["matches"] = [m.to_dict() for m in ordered[:limit]]
        if ordered:
            payload["first_match"] = ordered[0].summary()
            payload["last_match"] = ordered[-1].summary()
        return payload

    def head_to_head(
        self,
        team: str,
        opponent: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict:
        """Compare two teams head-to-head across the dataset."""
        team_key, error = self._resolve_or_error(team)
        if team_key is None:
            return error
        opponent_key, error = self._resolve_or_error(opponent)
        if opponent_key is None:
            return error
        team_display = self.registry.display(team_key)
        opponent_display = self.registry.display(opponent_key)

        pool = self._by_team.get(team_key, [])
        pool = [m for m in pool if m.involves_pair(team_key, opponent_key)]
        if competition:
            comp_key = self._resolve_competition_key(competition)
            if comp_key is None:
                return {"error": f"Unknown competition '{competition}'"}
            pool = [m for m in pool if m.competition_key == comp_key]
        if season is not None:
            pool = [m for m in pool if m.season == season]

        summary = {
            "matches": 0, "team_wins": 0, "opponent_wins": 0, "draws": 0,
            "team_goals": 0, "opponent_goals": 0,
        }
        for match in pool:
            if not match.has_result:
                continue
            summary["matches"] += 1
            team_goals = (match.home_goals if match.home_key == team_key
                          else match.away_goals)
            opponent_goals = (match.away_goals if match.home_key == team_key
                              else match.home_goals)
            summary["team_goals"] += team_goals
            summary["opponent_goals"] += opponent_goals
            if team_goals > opponent_goals:
                summary["team_wins"] += 1
            elif team_goals < opponent_goals:
                summary["opponent_wins"] += 1
            else:
                summary["draws"] += 1

        ordered = self._sort_matches(pool)
        return {
            "team": team_display,
            "opponent": opponent_display,
            "competition": self._resolve_competition_name(competition)
            if competition else None,
            "season": season,
            "summary": summary,
            "total_matches": len(ordered),
            "matches": [m.to_dict() for m in ordered[:_DEFAULT_LIMIT]],
            "truncated": len(ordered) > _DEFAULT_LIMIT,
        }

    # ------------------------------------------------------------------
    # Team statistics
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict:
        """Return win/draw/loss records and goals for a team."""
        team_key, error = self._resolve_or_error(team)
        if team_key is None:
            return error
        team_display = self.registry.display(team_key)
        pool = self._by_team.get(team_key, [])
        if competition:
            comp_key = self._resolve_competition_key(competition)
            if comp_key is None:
                return {"error": f"Unknown competition '{competition}'"}
            pool = [m for m in pool if m.competition_key == comp_key]
        if season is not None:
            pool = [m for m in pool if m.season == season]
        venue_norm = norm_text(venue) if venue else None
        if venue_norm in ("home", "casa"):
            pool = [m for m in pool if m.home_key == team_key]
        elif venue_norm in ("away", "fora"):
            pool = [m for m in pool if m.away_key == team_key]

        overall = self._record_for(team_key, team_display, pool)
        home_pool = [m for m in pool if m.home_key == team_key]
        away_pool = [m for m in pool if m.away_key == team_key]
        by_competition = []
        for comp_key in sorted({m.competition_key for m in pool}):
            comp_matches = [m for m in pool if m.competition_key == comp_key]
            record = self._record_for(team_key, team_display, comp_matches)
            record_dict = record.to_dict()
            record_dict["competition"] = COMPETITIONS.get(comp_key, comp_key)
            by_competition.append(record_dict)
        return {
            "team": team_display,
            "filters": {"season": season, "competition": competition,
                        "venue": venue},
            "overall": overall.to_dict(),
            "home": self._record_for(team_key, team_display, home_pool).to_dict(),
            "away": self._record_for(team_key, team_display, away_pool).to_dict(),
            "by_competition": by_competition,
        }

    @staticmethod
    def _record_for(team_key: str, display: str, matches: list[Match]) -> TeamRecord:
        record = TeamRecord(team=team_key, display=display)
        for match in matches:
            if match.has_result:
                record.add_match(team_key, match)
        return record

    def team_competitions(self, team: str) -> dict:
        """List the competitions and seasons a team appears in."""
        team_key, error = self._resolve_or_error(team)
        if team_key is None:
            return error
        pool = self._by_team.get(team_key, [])
        by_comp: dict[str, list[Match]] = defaultdict(list)
        for match in pool:
            by_comp[match.competition_key].append(match)
        competitions = []
        for comp_key, matches in sorted(by_comp.items()):
            seasons = sorted({m.season for m in matches if m.season is not None})
            competitions.append({
                "competition": COMPETITIONS.get(comp_key, comp_key),
                "key": comp_key,
                "matches": len(matches),
                "seasons": seasons,
                "first_match": self._sort_matches(matches)[0].summary()
                if matches else None,
                "last_match": self._sort_matches(matches)[-1].summary()
                if matches else None,
            })
        return {
            "team": self.registry.display(team_key),
            "competitions": competitions,
            "total_matches": len(pool),
        }

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------
    def standings(self, competition: str = "Brasileirão Série A",
                  season: int | None = None) -> dict:
        """Compute a league table from match results."""
        comp_key = self._resolve_competition_key(competition)
        if comp_key is None:
            return {"error": f"Unknown competition '{competition}'",
                    "known_competitions": list(COMPETITIONS.values())}
        if comp_key not in LEAGUE_COMPETITIONS:
            return {
                "error": f"Standings are only computed for league competitions "
                         f"({', '.join(COMPETITIONS[k] for k in LEAGUE_COMPETITIONS)}).",
                "competition": COMPETITIONS[comp_key],
            }
        if season is None:
            seasons = sorted({
                m.season for m in self._pool(comp_key)
                if m.season is not None
            })
            return {
                "error": "A season is required for standings.",
                "available_seasons": seasons,
            }
        pool = [m for m in self._pool(comp_key, season) if m.has_result]
        if not pool:
            return {"error": f"No matches found for {COMPETITIONS[comp_key]} "
                             f"season {season} in the dataset."}
        records: dict[str, TeamRecord] = {}
        for match in pool:
            for key in (match.home_key, match.away_key):
                records.setdefault(
                    key, TeamRecord(team=key, display=self.registry.display(key))
                )
                records[key].add_match(key, match)
        table = sorted(
            records.values(),
            key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for, r.team),
        )
        rows = [record.to_dict() for record in table]
        for position, row in enumerate(rows, start=1):
            row["position"] = position
        relegated_count = 4 if len(rows) >= 16 else 2 if len(rows) >= 6 else 0
        return {
            "competition": COMPETITIONS[comp_key],
            "season": season,
            "matches_considered": len(pool),
            "table": rows,
            "champion": rows[0]["display"] if rows else None,
            "relegated": [row["display"] for row in rows[-relegated_count:]]
            if relegated_count else [],
        }

    def competition_info(self, competition: str | None = None) -> dict:
        """Summarize available competitions, seasons and sources."""
        if competition:
            comp_key = self._resolve_competition_key(competition)
            if comp_key is None:
                return {"error": f"Unknown competition '{competition}'",
                        "known_competitions": list(COMPETITIONS.values())}
            pool = self._pool(comp_key)
            seasons = {}
            for match in pool:
                seasons.setdefault(match.season, {"matches": 0, "sources": set()})
                seasons[match.season]["matches"] += 1
                seasons[match.season]["sources"].add(match.source)
            season_rows = [
                {
                    "season": season,
                    "matches": data["matches"],
                    "sources": sorted(data["sources"]),
                }
                for season, data in sorted(seasons.items(), key=lambda kv: kv[0] or 0)
            ]
            return {
                "competition": COMPETITIONS[comp_key],
                "key": comp_key,
                "total_matches": len(pool),
                "seasons": season_rows,
                "source_labels": SOURCE_LABELS,
            }
        infos = []
        for comp_key, display in COMPETITIONS.items():
            pool = self._pool(comp_key)
            seasons = sorted({m.season for m in pool if m.season is not None})
            infos.append({
                "competition": display,
                "key": comp_key,
                "total_matches": len(pool),
                "seasons": seasons,
                "sources": sorted({m.source for m in pool}),
            })
        return {"competitions": infos}

    # ------------------------------------------------------------------
    # Derbies
    # ------------------------------------------------------------------
    def derbies(self, season: int | None = None,
                competition: str | None = None) -> dict:
        """Find matches between traditional rival teams."""
        pool = self._pool(competition, season)
        results = []
        for name, key_a, key_b in DERBIES:
            matches = [
                m for m in pool
                if m.involves_pair(key_a, key_b)
            ]
            if not matches:
                continue
            ordered = self._sort_matches(matches)
            summary = {
                "matches": 0, "team_a_wins": 0, "team_b_wins": 0, "draws": 0,
            }
            for match in matches:
                if not match.has_result:
                    continue
                summary["matches"] += 1
                winner = match.winner_key()
                if winner == key_a:
                    summary["team_a_wins"] += 1
                elif winner == key_b:
                    summary["team_b_wins"] += 1
                else:
                    summary["draws"] += 1
            results.append({
                "derby": name,
                "teams": [self.registry.display(key_a), self.registry.display(key_b)],
                "record": summary,
                "total_matches": len(ordered),
                "recent_matches": [m.summary() for m in ordered[-5:]][::-1],
            })
        return {
            "season": season,
            "derbies": results,
            "note": "Derby pairs follow the traditional Brazilian rivalries.",
        }

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------
    def biggest_wins(self, competition: str | None = None,
                     season: int | None = None, n: int = 10) -> dict:
        """Return the biggest winning margins in the dataset."""
        pool = [m for m in self._pool(competition, season) if m.has_result]
        ranked = sorted(
            pool,
            key=lambda m: (-m.goal_margin(), -m.total_goals, m.date or date.min),
        )
        wins = []
        for match in ranked[:n]:
            entry = match.to_dict()
            entry["margin"] = match.goal_margin()
            wins.append(entry)
        return {
            "competition": self._resolve_competition_name(competition)
            if competition else None,
            "season": season,
            "wins": wins,
        }

    def league_statistics(self, competition: str | None = None,
                          season: int | None = None,
                          source: str | None = None) -> dict:
        """Aggregate goal and result statistics for a set of matches."""
        pool = self._pool(competition, season, source)
        valid = [m for m in pool if m.has_result]
        if not valid:
            return {"error": "No matches with results found for the given filters."}
        stats = self._aggregate(valid)
        payload: dict = {
            "competition": self._resolve_competition_name(competition)
            if competition else "all competitions",
            "season": season,
            "source": source,
        }
        payload.update(stats)
        if competition is None and season is None:
            payload["by_competition"] = []
            for comp_key in sorted({m.competition_key for m in valid}):
                comp_matches = [m for m in valid if m.competition_key == comp_key]
                entry = {"competition": COMPETITIONS.get(comp_key, comp_key)}
                entry.update(self._aggregate(comp_matches))
                payload["by_competition"].append(entry)
        return payload

    @staticmethod
    def _aggregate(matches: list[Match]) -> dict:
        total = len(matches)
        goals = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.winner_key() == m.home_key)
        away_wins = sum(1 for m in matches if m.winner_key() == m.away_key)
        draws = total - home_wins - away_wins
        home_goals = sum(m.home_goals for m in matches)
        away_goals = sum(m.away_goals for m in matches)
        biggest = max(
            matches,
            key=lambda m: (m.goal_margin(), m.total_goals),
        )
        return {
            "matches": total,
            "goals": goals,
            "avg_goals_per_match": round(goals / total, 2),
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate": round(home_wins / total, 3),
            "draw_rate": round(draws / total, 3),
            "away_win_rate": round(away_wins / total, 3),
            "avg_home_goals": round(home_goals / total, 2),
            "avg_away_goals": round(away_goals / total, 2),
            "biggest_win": biggest.summary(),
        }

    def best_records(self, competition: str | None = None,
                     season: int | None = None, venue: str = "home",
                     min_matches: int = 20, n: int = 10) -> dict:
        """Rank teams by win rate at a venue (home, away or overall)."""
        pool = self._pool(competition, season)
        venue_norm = norm_text(venue)
        matches_by_team: dict[str, list[tuple[str, Match]]] = defaultdict(list)
        for match in pool:
            if not match.has_result:
                continue
            if venue_norm in ("home", "casa"):
                matches_by_team[match.home_key].append((match.home_key, match))
            elif venue_norm in ("away", "fora"):
                matches_by_team[match.away_key].append((match.away_key, match))
            else:
                matches_by_team[match.home_key].append((match.home_key, match))
                matches_by_team[match.away_key].append((match.away_key, match))
        records = []
        for team_key, entries in matches_by_team.items():
            record = TeamRecord(team=team_key,
                                display=self.registry.display(team_key))
            for team_key_of_match, match in entries:
                record.add_match(team_key_of_match, match)
            if record.matches >= min_matches:
                records.append(record)
        records.sort(key=lambda r: (-r.win_rate, -r.wins, -r.points, r.team))
        return {
            "venue": venue,
            "competition": self._resolve_competition_name(competition)
            if competition else None,
            "season": season,
            "min_matches": min_matches,
            "records": [record.to_dict() for record in records[:n]],
        }

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------
    def search_players(
        self,
        name: str | None = None,
        club: str | None = None,
        nationality: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict:
        """Search the FIFA player database with flexible filters."""
        name_norm = norm_text(name) if name else None
        club_norm = norm_text(club) if club else None
        nationality_norm = strip_accents(nationality).strip().lower() if nationality else None
        position_codes = self._resolve_position(position)
        club_resolution = self.registry.resolve(club) if club else None
        strict_club = club_resolution.key if club_resolution and \
            club_resolution.found else None

        filtered = []
        for player in self.players:
            if name_norm and name_norm not in norm_text(player.name):
                continue
            if nationality_norm and strip_accents(player.nationality).lower() != nationality_norm:
                continue
            if club_norm:
                if strict_club:
                    if player.club_key != strict_club:
                        continue
                elif club_norm not in norm_text(player.club):
                    continue
            if position_codes and player.position not in position_codes:
                continue
            if min_overall is not None and (
                player.overall is None or player.overall < min_overall
            ):
                continue
            if max_overall is not None and (
                player.overall is None or player.overall > max_overall
            ):
                continue
            filtered.append(player)
        filtered.sort(key=lambda p: (-(p.overall or 0), p.name))
        return {
            "players": [p.to_dict() for p in filtered[:limit]],
            "total": len(filtered),
            "truncated": len(filtered) > limit,
        }

    def top_players(self, club: str | None = None,
                    nationality: str | None = None,
                    position: str | None = None,
                    n: int = 10) -> dict:
        """Return the highest-rated players matching the filters."""
        result = self.search_players(
            club=club, nationality=nationality, position=position, limit=n
        )
        if "error" in result:
            return result
        return {
            "players": result["players"],
            "total": result["total"],
            "note": "Players ranked by FIFA overall rating.",
        }

    def players_by_club(self, nationality: str = "Brazil") -> dict:
        """Aggregate players of one nationality playing at Brazilian clubs."""
        nationality_norm = strip_accents(nationality).strip().lower()
        by_club: dict[str, list[Player]] = defaultdict(list)
        for player in self.players:
            if strip_accents(player.nationality).lower() != nationality_norm:
                continue
            if player.club_key in self._brazilian_team_keys:
                by_club[player.club_key].append(player)
        clubs = []
        for club_key, players in by_club.items():
            overalls = [p.overall for p in players if p.overall is not None]
            top = sorted(
                players, key=lambda p: (-(p.overall or 0), p.name)
            )[:3]
            clubs.append({
                "club": self.registry.display(club_key),
                "players": len(players),
                "avg_overall": round(sum(overalls) / len(overalls), 1) if overalls else None,
                "top_players": [
                    {"name": p.name, "overall": p.overall, "position": p.position}
                    for p in top
                ],
            })
        clubs.sort(key=lambda entry: (-entry["players"], entry["club"]))
        return {
            "nationality": nationality,
            "clubs": clubs,
            "note": f"{nationality} players at Brazilian clubs present in the "
                    f"match datasets.",
        }

    @staticmethod
    def _resolve_position(position: str | None) -> list[str] | None:
        if not position:
            return None
        code = position.strip().upper()
        if code in POSITION_CODES:
            return [code]
        return POSITION_GROUPS.get(position.strip().lower())


_service: SoccerDataService | None = None


def get_service() -> SoccerDataService:
    """Return the process-wide service instance, loading data on first use."""
    global _service
    if _service is None:
        _service = SoccerDataService()
    return _service
