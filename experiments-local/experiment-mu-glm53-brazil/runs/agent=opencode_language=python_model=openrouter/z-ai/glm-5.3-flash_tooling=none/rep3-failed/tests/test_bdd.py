"""BDD-style test suite for the Brazilian Soccer MCP server.

The scenarios mirror the Gherkin specifications in TASK.md and the success
criteria: match/team/player/competition/statistics queries, team-name
normalization, date formats, cross-file queries, performance budgets and an
end-to-end MCP protocol smoke test.
"""

from __future__ import annotations

import asyncio
import re
import time

import pytest

from bsoccer.data_loader import load_all
from bsoccer.normalization import parse_date, resolve_team
from bsoccer.queries import KnowledgeBase


@pytest.fixture(scope="session")
def kb() -> KnowledgeBase:
    return KnowledgeBase()


@pytest.fixture(scope="session")
def raw() -> tuple[list, list]:
    return load_all()


# ---------------------------------------------------------------------------
# Feature: Data loading and normalization
# ---------------------------------------------------------------------------

class TestDataLoading:
    """All six datasets must be loadable and queryable."""

    def test_all_six_csv_files_load(self, raw):
        matches, players = raw
        # Given the six Kaggle CSV datasets on disk
        # When they are loaded
        # Then every dataset contributes records
        sources = {m.source_file for m in matches}
        assert sources == {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }
        assert len(players) == 18207
        assert len(matches) >= 23000

    def test_expected_match_counts_per_file(self, raw):
        # Then the row counts match the documented dataset sizes
        matches, _ = raw
        by_file = {}
        for m in matches:
            by_file[m.source_file] = by_file.get(m.source_file, 0) + 1
        assert by_file["Brasileirao_Matches.csv"] == 4180
        assert by_file["Brazilian_Cup_Matches.csv"] == 1337
        assert by_file["Libertadores_Matches.csv"] == 1255
        assert by_file["BR-Football-Dataset.csv"] == 10296
        assert by_file["novo_campeonato_brasileiro.csv"] == 6886


class TestTeamNameNormalization:
    """Implementation must normalize team names for consistent matching."""

    def test_state_suffix_variants_resolve_together(self):
        assert resolve_team("Palmeiras-SP") == resolve_team("Palmeiras")
        assert resolve_team("Flamengo-RJ") == resolve_team("Flamengo")

    def test_space_dash_and_accent_variants_resolve_together(self):
        assert resolve_team("América - MG") == resolve_team("America MG")
        assert resolve_team("Sao Paulo") == resolve_team("São Paulo")
        assert resolve_team("Avaí - SC") == resolve_team("Avai")

    def test_full_name_and_short_name_resolve_together(self):
        assert resolve_team("Athletico-PR") == resolve_team("Athletico Paranaense")
        assert resolve_team("Vasco") == resolve_team("Vasco da Gama-RJ")
        assert resolve_team("Sport-PE") == resolve_team("Sport Recife")

    def test_distinct_clubs_are_not_merged(self):
        assert resolve_team("Botafogo-RJ") != resolve_team("Botafogo-PB")
        assert resolve_team("Atlético-MG") != resolve_team("Atlético-GO")
        assert resolve_team("Santos") != resolve_team("Santos AP")
        assert resolve_team("América-MG") != resolve_team("América-RN")

    def test_cross_file_matches_share_canonical_name(self, kb):
        # 'São Paulo' (novo dataset), 'Sao Paulo' (BR-Football) and
        # 'Sao Paulo-SP' (Brasileirão) must all count as the same team.
        # 2019 Serie A exists in two datasets but must dedupe to 38 matches.
        r = kb.team_statistics("Sao Paulo-SP", season=2019)
        assert r["team"] == "São Paulo"
        assert r["by_competition"]["Brasileirão Série A"]["played"] == 38
        assert r["overall"]["played"] >= 38


class TestDateParsing:
    """Implementation must handle multiple date formats."""

    def test_iso_datetime(self):
        d, dt = parse_date("2012-05-19 18:30:00")
        assert d.isoformat() == "2012-05-19"
        assert dt is not None and dt.hour == 18

    def test_brazilian_format(self):
        d, dt = parse_date("29/03/2003")
        assert d.isoformat() == "2003-03-29"
        assert dt is None

    def test_plain_iso_date(self):
        d, _ = parse_date("2023-09-24")
        assert d.isoformat() == "2023-09-24"

    def test_invalid_and_empty(self):
        assert parse_date("") == (None, None)
        assert parse_date("NA") == (None, None)


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------

class TestMatchQueries:
    def test_find_matches_between_two_teams(self, kb):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        # Then I should receive a list of matches
        # And each match should have date, scores, and competition
        r = kb.search_matches(team="Flamengo", opponent="Fluminense")
        assert r["count"] > 0
        for m in r["matches"]:
            assert m["home_team"] in ("Flamengo", "Fluminense")
            assert m["away_team"] in ("Flamengo", "Fluminense")
            assert m["date"], "each match must carry a date"
            assert m["competition"], "each match must carry a competition"
            assert m["home_goal"] is not None and m["away_goal"] is not None
        # And the response includes a head-to-head summary
        h2h = r["head_to_head"]
        assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] >= r["count"]

    def test_fla_flu_derby_finds_both_sides_of_fixtures(self, kb):
        # Fla-Flu derbies appear once per dataset occurrence; dedupe keeps
        # one record per fixture across overlapping datasets.
        r = kb.search_matches(team="Flamengo-RJ", opponent="Fluminense-RJ")
        assert r["count"] >= 40

    def test_matches_by_team_and_season(self, kb):
        # When I ask "What matches did Palmeiras play in 2023?"
        r = kb.search_matches(team="Palmeiras", season=2023)
        assert r["count"] >= 38  # full Serie A season
        seasons = {m["season"] for m in r["matches"]}
        assert seasons == {2023}

    def test_matches_by_competition_finals(self, kb):
        # When I "Find all Copa do Brasil finals"
        # Then each identified final is a two-legged tie between the same teams
        r = kb.search_matches(competition="Copa do Brasil", stage="final", limit=100)
        assert r["count"] >= 16  # ~8 seasons with finals in the dataset
        by_season = {}
        for m in r["matches"]:
            by_season.setdefault(m["season"], []).append(m)
        for season, finals in by_season.items():
            teams = {tuple(sorted((m["home_team"], m["away_team"]))) for m in finals}
            assert len(teams) == 1, f"season {season} final must involve one pair of teams"

    def test_matches_by_date_range(self, kb):
        r = kb.search_matches(team="Corinthians", date_from="2022-01-01", date_to="2022-12-31")
        assert r["count"] > 0
        for m in r["matches"]:
            assert m["date"].startswith("2022")

    def test_matches_by_round(self, kb):
        r = kb.search_matches(competition="Brasileirão", season=2019, round=38, limit=50)
        assert r["count"] == 20  # last round: all 20 teams play
        for m in r["matches"]:
            assert m["round"] == "38"


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------

class TestTeamQueries:
    def test_get_team_statistics(self, kb):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        # Then I should receive wins, losses, draws, and goals
        r = kb.team_statistics("Palmeiras", season=2023)
        stat = r["overall"]
        assert stat["played"] == stat["wins"] + stat["draws"] + stat["losses"]
        assert stat["goals_for"] > 0 and stat["goals_against"] >= 0
        assert 0 <= stat["win_rate"] <= 100
        assert r["home"]["played"] + r["away"]["played"] == stat["played"]

    def test_corinthians_home_record_2022(self, kb):
        # "What is Corinthians' home record in 2022?"
        r = kb.team_statistics("Corinthians", season=2022, competition="Brasileirão")
        home = r["home"]
        assert home["played"] == 19  # 38-round Serie A -> 19 home matches
        assert home["wins"] + home["draws"] + home["losses"] == 19

    def test_team_statistics_by_competition_breakdown(self, kb):
        # "What competitions has Palmeiras played in?" -> per-competition split
        r = kb.team_statistics("Palmeiras", season=2021)
        assert set(r["by_competition"]) >= {"Brasileirão Série A", "Copa Libertadores"}
        assert r["by_competition"]["Copa Libertadores"]["played"] > 0

    def test_head_to_head_comparison(self, kb):
        # "Compare Palmeiras and Santos head-to-head"
        r = kb.head_to_head("Palmeiras", "Santos")
        s = r["summary"]
        assert s["team_a_wins"] + s["team_b_wins"] + s["draws"] == r["total_matches"]
        assert s["goals_team_a"] > 0 and s["goals_team_b"] > 0

    def test_unknown_team_reports_candidates(self, kb):
        r = kb.team_statistics("Xyz United")
        assert "error" in r
        assert "candidates" in r

    def test_fuzzy_team_lookup(self, kb):
        r = kb.team_statistics("palmeir", season=2023)
        assert r["team"] == "Palmeiras"


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    def test_find_all_brazilian_players(self, kb):
        # "Find all Brazilian players in the dataset"
        r = kb.search_players(nationality="Brazil", limit=100)
        assert r["count"] >= 800
        for p in r["players"]:
            assert p["nationality"] == "Brazil"

    def test_top_rated_players_sorted(self, kb):
        # "Who are the top Brazilian players?"
        r = kb.search_players(nationality="Brazil", limit=5)
        overalls = [p["overall"] for p in r["players"]]
        assert overalls == sorted(overalls, reverse=True)
        assert r["players"][0]["name"] == "Neymar Jr"
        assert r["players"][0]["overall"] == 92

    def test_players_by_club_with_summary(self, kb):
        # "Which players play for Ceará?" (FIFA club: 'Ceará Sporting Club')
        r = kb.search_players(club="Ceará", limit=50)
        assert r["count"] == 20
        summary = r["club_summary"]
        assert summary["player_count"] == r["count"]
        assert summary["average_overall"] > 50

    def test_players_by_position(self, kb):
        # "Show me all forwards from São Paulo FC" (position filter)
        r = kb.search_players(nationality="Brazil", position="ST", min_overall=80, limit=20)
        assert r["count"] > 0
        assert all(p["position"] == "ST" for p in r["players"])

    def test_player_profile_lookup(self, kb):
        # "Who is Neymar?" -> search FIFA player data by name
        r = kb.player_profile("Neymar")
        assert r["player"]["name"] == "Neymar Jr"
        assert r["player"]["skills"]["Dribbling"] >= 90

    def test_player_profile_partial_name(self, kb):
        r = kb.player_profile("alisson")
        assert "Alisson" in r["player"]["name"]

    def test_player_profile_unknown(self, kb):
        r = kb.player_profile("Zzzz Qqqq")
        assert "error" in r


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------

class TestCompetitionQueries:
    def test_who_won_the_2019_brasileirao(self, kb):
        # "Who won the 2019 Brasileirão?" — spec example: Flamengo 90 pts
        s = kb.standings("Brasileirão", 2019)
        top = s["standings"][0]
        assert top["team"] == "Flamengo"
        assert top["points"] == 90
        assert top["note"] == "Champion"

    def test_standings_math_is_consistent(self, kb):
        s = kb.standings("Brasileirão", 2019)
        for row in s["standings"]:
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]
            assert row["points"] == row["wins"] * 3 + row["draws"]
        total_points = sum(row["points"] for row in s["standings"])
        total_played = sum(row["played"] for row in s["standings"])
        assert total_played == 760  # 380 matches x 2
        assert total_points == 3 * 380 - total_played // 2  # 3 per win, 2 shared per draw

    def test_relegated_teams_2020(self, kb):
        # "Which teams were relegated in 2020?" (bottom 4 of Serie A)
        s = kb.standings("Serie A", 2020)
        relegated = [row["team"] for row in s["standings"][-4:]]
        assert set(relegated) == {"Vasco", "Goiás", "Coritiba", "Botafogo"}
        assert all(row["note"].startswith("Relegation") for row in s["standings"][-4:])

    def test_standings_before_brasileirao_matches_file(self, kb):
        # 2005 exists only in the historical dataset and had 22 teams
        s = kb.standings("Brasileirão", 2005)
        assert len(s["standings"]) == 22
        assert s["standings"][0]["team"] == "Corinthians"
        assert s["standings"][0]["points"] == 81

    def test_standings_unknown_season(self, kb):
        r = kb.standings("Brasileirão", 1999)
        assert "error" in r

    def test_competition_statistics(self, kb):
        r = kb.competition_statistics("Brasileirão", 2019)
        assert r["match_count"] == 380
        assert 2.0 < r["average_goals_per_match"] < 3.5
        assert r["home_win_rate"] + r["draw_rate"] + r["away_win_rate"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    def test_average_goals_and_home_advantage(self, kb):
        # "What's the average goals per match in the Brasileirão?"
        r = kb.competition_statistics("Brasileirão")
        assert r["match_count"] > 5000
        assert 2.0 < r["average_goals_per_match"] < 3.5
        # Home advantage: home win rate should exceed away win rate
        assert r["home_win_rate"] > r["away_win_rate"]

    def test_biggest_wins_sorted_by_margin(self, kb):
        # "Show me the biggest wins in the dataset"
        r = kb.biggest_wins(limit=10)
        margins = [abs(m["home_goal"] - m["away_goal"]) for m in r["wins"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 6

    def test_compare_seasons(self, kb):
        # "Compare the 2018 and 2019 seasons"
        r = kb.compare_seasons("Brasileirão", 2018, 2019)
        comp = r["comparison"]
        assert comp["match_count"]["season_a"] == 380
        assert comp["match_count"]["season_b"] == 380

    def test_season_aggregates_no_double_counting(self, kb):
        # 2019 Serie A appears in two datasets; the aggregate must count
        # each fixture once.
        r = kb.competition_statistics("Brasileirão", 2019)
        assert r["match_count"] == 380


# ---------------------------------------------------------------------------
# Feature: Cross-file queries
# ---------------------------------------------------------------------------

class TestCrossFileQueries:
    def test_team_overview_combines_matches_and_players(self, kb):
        # Cross-file: match datasets + FIFA player dataset for one team
        r = kb.team_overview("Santos")
        assert r["total_matches"] > 800
        assert "Copa Libertadores" in r["matches_by_competition"]
        players = r["fifa_players"]
        assert players is not None
        assert players["player_count"] == 20
        assert players["top_players"], "club roster must list top players"

    def test_club_without_fifa_license_reports_gracefully(self, kb):
        # Flamengo is not licensed in FIFA 19, so no roster is available
        r = kb.team_overview("Flamengo")
        assert r["fifa_players"] is None
        assert "FIFA" in (r.get("fifa_note") or "")

    def test_dataset_summary(self, kb):
        s = kb.summary()
        assert s["matches_loaded"] >= 23000
        assert s["players_loaded"] == 18207
        assert len(s["datasets"]) == 6


# ---------------------------------------------------------------------------
# Feature: Query performance
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_simple_lookup_under_2_seconds(self, kb):
        start = time.perf_counter()
        kb.search_matches(team="Flamengo", opponent="Corinthians")
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"simple lookup took {elapsed:.2f}s"

    def test_aggregate_query_under_5_seconds(self, kb):
        start = time.perf_counter()
        kb.competition_statistics("Brasileirão")
        kb.team_statistics("Palmeiras")
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"aggregate query took {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# Feature: MCP server (end-to-end protocol smoke test)
# ---------------------------------------------------------------------------

class TestMCPServer:
    """Drive the MCP server in-process through the MCP client."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_list_tools(self):
        from bsoccer.server import server as mcp_server
        from mcp.client.client import Client

        async def scenario():
            async with Client(mcp_server) as client:
                return await client.list_tools()

        tools = self._run(scenario())
        names = {t.name for t in tools.tools}
        assert {
            "search_matches", "head_to_head", "team_statistics", "standings",
            "search_players", "player_profile", "team_overview",
            "competition_statistics", "biggest_wins", "compare_seasons",
            "list_teams", "dataset_summary",
        } <= names

    def test_call_tools(self):
        from bsoccer.server import server as mcp_server
        from mcp.client.client import Client

        async def scenario():
            async with Client(mcp_server) as client:
                matches = await client.call_tool(
                    "search_matches",
                    {"team": "Flamengo", "opponent": "Fluminense", "limit": 5},
                )
                table = await client.call_tool(
                    "standings", {"competition": "Brasileirão", "season": 2019},
                )
                players = await client.call_tool(
                    "search_players", {"nationality": "Brazil", "limit": 3},
                )
                return matches, table, players

        matches, table, players = self._run(scenario())
        matches_text = _extract_text(matches)
        assert "Flamengo" in matches_text and re.search(r"\d{4}-\d{2}-\d{2}", matches_text)
        assert "Head-to-head" in matches_text
        table_text = _extract_text(table)
        assert "Flamengo — 90 pts" in table_text
        players_text = _extract_text(players)
        assert "Neymar Jr" in players_text


def _extract_text(result) -> str:
    parts = []
    for block in result.content:
        if getattr(block, "text", None):
            parts.append(block.text)
    return "\n".join(parts)
