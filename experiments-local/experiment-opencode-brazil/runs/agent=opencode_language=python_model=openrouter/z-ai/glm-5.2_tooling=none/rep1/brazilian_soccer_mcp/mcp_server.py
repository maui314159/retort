import json
import os
from dataclasses import asdict
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .data_loader import load_all
from .query_engine import QueryEngine

_engine: Optional[QueryEngine] = None


def _engine_singleton() -> QueryEngine:
    global _engine
    if _engine is None:
        data_dir = os.environ.get("BRAZILIAN_SOCCER_DATA", "data/kaggle")
        _engine = QueryEngine(load_all(data_dir))
    return _engine


def _to_jsonable(obj):
    if hasattr(obj, "to_dict"):
        return _to_jsonable(obj.to_dict())
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def build_server(engine: Optional[QueryEngine] = None) -> FastMCP:
    if engine is None:
        engine = _engine_singleton()

    mcp = FastMCP("brazilian-soccer-mcp")

    @mcp.tool()
    def search_matches(
        team: Optional[str] = None,
        vs_team: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        side: str = "either",
        limit: Optional[int] = None,
    ) -> str:
        """Find matches by team, opponent, competition, season or date range.

        competition: 'Brasileirao', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'.
        side: 'either' (default), 'home' or 'away' (relative to `team`).
        """
        result = engine.search_matches(
            team=team, vs_team=vs_team, competition=competition, season=season,
            date_from=date_from, date_to=date_to, side=side, limit=limit,
        )
        return json.dumps(_to_jsonable(result), ensure_ascii=False)

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> str:
        """Compare two teams head-to-head across the dataset."""
        return json.dumps(
            _to_jsonable(engine.head_to_head(team_a, team_b, competition)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def team_statistics(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_away: str = "overall",
    ) -> str:
        """Return wins/draws/losses and goals for a team.

        home_away: 'overall' (default), 'home' or 'away'.
        """
        return json.dumps(
            _to_jsonable(engine.team_statistics(team, season, competition, home_away)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def top_teams_by_record(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        home_away: str = "overall",
        metric: str = "win_rate",
        limit: int = 10,
    ) -> str:
        """Rank teams by win_rate, wins or goals_for."""
        return json.dumps(
            _to_jsonable(engine.top_teams_by_record(
                competition, season, home_away, metric, limit
            )),
            ensure_ascii=False,
        )

    @mcp.tool()
    def most_goals_scored(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Teams that scored the most goals in a competition/season."""
        return json.dumps(
            _to_jsonable(engine.most_goals_scored(competition, season, limit)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def search_player(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
        sort_by: str = "Overall",
    ) -> str:
        """Search the FIFA player database by name, nationality, club, position or rating."""
        return json.dumps(
            _to_jsonable(engine.search_player(
                name=name, nationality=nationality, club=club, position=position,
                min_overall=min_overall, limit=limit, sort_by=sort_by,
            )),
            ensure_ascii=False,
        )

    @mcp.tool()
    def top_players(
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """Top-rated players filtered by nationality/club/position."""
        return json.dumps(
            _to_jsonable(engine.top_players(nationality, club, position, limit)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def players_at_club(club: str) -> str:
        """Players at a given club (Brazilian clubs normalized)."""
        return json.dumps(
            _to_jsonable(engine.players_at_club(club)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def competition_standings(
        competition: str, season: int, limit: Optional[int] = None,
    ) -> str:
        """Standings calculated from match results for a competition/season."""
        return json.dumps(
            _to_jsonable(engine.competition_standings(competition, season, limit)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def competition_champion(competition: str, season: int) -> str:
        """Return the champion (top of standings) of a competition/season."""
        return json.dumps(
            _to_jsonable(engine.competition_champion(competition, season)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def relegated_teams(competition: str, season: int, n: int = 4) -> str:
        """Bottom n teams of a competition/season."""
        return json.dumps(
            _to_jsonable(engine.relegated_teams(competition, season, n)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def average_goals_per_match(
        competition: Optional[str] = None, season: Optional[int] = None,
    ) -> str:
        """Average goals per match overall or for a competition/season."""
        return json.dumps(
            engine.average_goals_per_match(competition, season),
            ensure_ascii=False,
        )

    @mcp.tool()
    def home_vs_away_performance(
        competition: Optional[str] = None, season: Optional[int] = None,
    ) -> str:
        """Home win / away win / draw rates."""
        return json.dumps(
            engine.home_vs_away_performance(competition, season),
            ensure_ascii=False,
        )

    @mcp.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Biggest victories (goal difference) in the dataset."""
        return json.dumps(
            _to_jsonable(engine.biggest_wins(competition, season, limit)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def derbies(
        season: Optional[int] = None, competition: Optional[str] = None,
    ) -> str:
        """Famous Brazilian derby matches (Fla-Flu, Gre-Nal, etc.)."""
        return json.dumps(
            _to_jsonable(engine.derbies(season, competition)),
            ensure_ascii=False,
        )

    @mcp.tool()
    def match_stats(
        team: Optional[str] = None,
        vs_team: Optional[str] = None,
        season: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Extended match statistics (corners, shots, attacks) when available."""
        return json.dumps(
            _to_jsonable(engine.match_stats(team, vs_team, season, limit)),
            ensure_ascii=False, default=str,
        )

    @mcp.tool()
    def data_coverage() -> str:
        """Summary of loaded datasets (counts, competitions, seasons)."""
        return json.dumps(
            _to_jsonable(engine.data_coverage()),
            ensure_ascii=False,
        )

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
