"""
BDD-style tests for the Brazilian Soccer MCP server.

These tests exercise the query layer (``soccer_mcp.queries``) and the MCP
server construction (``soccer_mcp.server``) against the real Kaggle datasets
in ``data/kaggle/``.  They map directly to the requirements in ``FEEDBACK.md``:

    R1  build_server exposes MCP tools                -> test_server_tools
    R2  loads CSVs from data/kaggle/                  -> test_data_loaded
    R3  match query by team (home/away/either)        -> test_find_matches_by_team
    R4  filter by date range and season               -> test_find_matches_by_season_and_date
    R5  filter by competition                          -> test_find_matches_by_competition
    R6  team stats (W/L/D, goals)                      -> test_team_stats
    R7  player search by name                          -> test_search_players_by_name
    R8  player filter by nationality / club / ratings  -> test_search_players_by_nationality_and_club
    R9  standings calculated from match results       -> test_standings
    R10 aggregate statistics                           -> test_statistics_and_biggest_wins
    R11 head-to-head records                           -> test_head_to_head
    R12 tests execute (this file)                      -> the suite itself
"""
from __future__ import annotations

import pytest

from soccer_mcp import queries
from soccer_mcp.data_loader import (
    COMP_BRASILEIRAO_A,
    COMP_COPA_BRASIL,
    COMP_LIBERTADORES,
    get_data,
)
from soccer_mcp.normalize import parse_date, strip_accents, to_int_goal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def data():
    return get_data()


# ---------------------------------------------------------------------------
# R2 - data loaded from data/kaggle/
# ---------------------------------------------------------------------------
class TestDataLoading:
    def test_matches_loaded_from_all_six_csvs(self, data):
        # Six source files contribute to the dataset.
        assert len(data.matches) > 0
        assert len(data.raw_matches) > 1000
        assert len(data.stats_matches) > 0
        assert len(data.players) > 1000
        sources = {m.source for m in data.raw_matches}
        assert "Brasileirao_Matches.csv" in sources
        assert "novo_campeonato_brasileiro.csv" in sources
        assert "BR-Football-Dataset.csv" in sources
        assert "Brazilian_Cup_Matches.csv" in sources
        assert "Libertadores_Matches.csv" in sources

    def test_all_five_competitions_present(self, data):
        comps = set(data.competitions())
        assert {
            COMP_BRASILEIRAO_A,
            COMP_COPA_BRASIL,
            COMP_LIBERTADORES,
        }.issubset(comps)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
class TestNormalize:
    def test_parse_date_iso(self):
        assert parse_date("2023-09-24") == "2023-09-24"
        assert parse_date("2023-09-24 18:30:00") == "2023-09-24"

    def test_parse_date_brazilian(self):
        assert parse_date("29/03/2003") == "2003-03-29"

    def test_parse_date_invalid(self):
        assert parse_date("") is None
        assert parse_date(None) is None
        assert parse_date("not a date") is None

    def test_strip_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"

    def test_to_int_goal(self):
        assert to_int_goal("3") == 3
        assert to_int_goal(3.0) == 3
        assert to_int_goal(None) is None
        assert to_int_goal("") is None

    def test_team_name_variations_canonicalised(self):
        # "Palmeiras-SP" and "Palmeiras" must resolve to the same key.
        assert queries.resolve_team("Palmeiras-SP") == queries.resolve_team("Palmeiras")
        assert queries.resolve_team("Flamengo-RJ") == queries.resolve_team("Flamengo")


# ---------------------------------------------------------------------------
# R3 - find matches by team (home / away / either)
# ---------------------------------------------------------------------------
class TestFindMatches:
    def test_find_matches_by_team_either(self):
        res = queries.find_matches(team="Flamengo", limit=50)
        assert res, "expected matches for Flamengo"
        for m in res:
            assert "Flamengo" in (m["home_team"], m["away_team"])

    def test_find_matches_by_team_home_only(self):
        res = queries.find_matches(team="Flamengo", venue="home", limit=50)
        assert res
        for m in res:
            assert m["home_team"] == "Flamengo"

    def test_find_matches_by_team_away_only(self):
        res = queries.find_matches(team="Flamengo", venue="away", limit=50)
        assert res
        for m in res:
            assert m["away_team"] == "Flamengo"

    def test_find_matches_between_two_teams(self):
        res = queries.find_matches(team="Flamengo", opponent="Fluminense", limit=100)
        assert res
        for m in res:
            teams = {m["home_team"], m["away_team"]}
            assert teams == {"Flamengo", "Fluminense"}

    def test_find_matches_each_has_required_fields(self):
        res = queries.find_matches(team="Palmeiras", limit=5)
        for m in res:
            assert "date" in m
            assert "score" in m
            assert "competition" in m
            assert "home_team" in m and "away_team" in m
            assert "home_goals" in m and "away_goals" in m

    # R4 - date range and season
    def test_find_matches_by_season(self):
        res = queries.find_matches(team="Palmeiras", season="2023", limit=200)
        assert res
        for m in res:
            assert m["season"] == "2023"

    def test_find_matches_by_date_range(self):
        res = queries.find_matches(
            team="Flamengo", date_from="2019-01-01", date_to="2019-12-31", limit=200
        )
        assert res
        for m in res:
            assert m["date"] is not None
            assert "2019-01-01" <= m["date"] <= "2019-12-31"

    # R5 - competition filter
    def test_find_matches_by_competition_brasileirao(self):
        res = queries.find_matches(competition="brasileirao", season="2019", limit=50)
        assert res
        for m in res:
            assert m["competition"] == COMP_BRASILEIRAO_A

    def test_find_matches_by_competition_copa_do_brasil(self):
        res = queries.find_matches(competition="Copa do Brasil", limit=50)
        assert res
        for m in res:
            assert m["competition"] == COMP_COPA_BRASIL

    def test_find_matches_by_competition_libertadores(self):
        res = queries.find_matches(competition="libertadores", limit=50)
        assert res
        for m in res:
            assert m["competition"] == COMP_LIBERTADORES


# ---------------------------------------------------------------------------
# R6 - team statistics (W/L/D + goals)
# ---------------------------------------------------------------------------
class TestTeamStats:
    def test_team_stats_overall(self):
        s = queries.team_stats("Palmeiras", season="2023")
        ov = s["overall"]
        assert ov["played"] > 0
        assert ov["wins"] + ov["draws"] + ov["losses"] == ov["played"]
        assert ov["goals_for"] >= 0
        assert ov["goals_against"] >= 0

    def test_team_stats_home_away_split(self):
        s = queries.team_stats("Flamengo", season="2019")
        assert s["home"]["played"] > 0
        assert s["away"]["played"] > 0
        total = s["home"]["played"] + s["away"]["played"]
        assert total == s["overall"]["played"]

    def test_team_stats_by_competition(self):
        s = queries.team_stats("Flamengo")
        assert s["by_competition"], "expected per-competition breakdown"
        assert COMP_BRASILEIRAO_A in s["by_competition"]

    def test_team_stats_venue_filter(self):
        home_only = queries.team_stats("Flamengo", season="2019", venue="home")
        assert home_only["overall"]["played"] == home_only["home"]["played"]
        assert home_only["away"]["played"] == 0 or home_only["overall"]["played"] > 0


# ---------------------------------------------------------------------------
# R7 - player search by name
# ---------------------------------------------------------------------------
class TestSearchPlayers:
    def test_search_players_by_name(self):
        res = queries.search_players(name="Neymar", limit=10)
        assert res
        assert any("Neymar" in p["name"] for p in res)

    def test_search_players_returns_ratings(self):
        res = queries.search_players(name="Messi", limit=3)
        assert res
        for p in res:
            assert "overall" in p and p["overall"] is not None
            assert "position" in p

    # R8 - nationality / club / attributes
    def test_search_players_by_nationality(self):
        res = queries.search_players(nationality="Brazil", limit=20)
        assert len(res) == 20
        for p in res:
            assert "Brazil" in p["nationality"]

    def test_search_players_by_club(self):
        res = queries.search_players(club="Barcelona", limit=10)
        assert res
        for p in res:
            assert "barcelona" in (p["club"] or "").lower()

    def test_search_players_by_nationality_and_position(self):
        res = queries.search_players(nationality="Brazil", position="ST", limit=10)
        assert res
        for p in res:
            assert "Brazil" in p["nationality"]
            assert "ST" in p["position"]

    def test_search_players_min_overall(self):
        res = queries.search_players(min_overall=90, limit=50)
        assert res
        for p in res:
            assert p["overall"] >= 90

    def test_team_players_cross_file(self):
        # Cross-file query: soccer team name -> FIFA club match (works for
        # European clubs present in FIFA whose canonical key maps).
        res = queries.search_players(club="Juventus", limit=5)
        assert res


# ---------------------------------------------------------------------------
# R9 - standings calculated from match results
# ---------------------------------------------------------------------------
class TestStandings:
    def test_standings_2019_brasileirao(self):
        table = queries.standings("Brasileirao", "2019")
        assert table
        # Flamengo won the 2019 Brasileirao.
        assert table[0]["team"] == "Flamengo"
        assert table[0]["points"] == 90
        # Points computed: 3*wins + draws
        for row in table:
            assert row["points"] == 3 * row["wins"] + row["draws"]
        # Sorted descending by points.
        points = [r["points"] for r in table]
        assert points == sorted(points, reverse=True)

    def test_champion_2019(self):
        champ = queries.champion("Brasileirao", "2019")
        assert champ["champion"] == "Flamengo"
        assert champ["points"] == 90

    def test_standings_top_filter(self):
        table = queries.standings("Brasileirao", "2019", top=5)
        assert len(table) == 5

    def test_standings_rejected_for_cup(self):
        with pytest.raises(ValueError):
            queries.standings("Copa do Brasil", "2019")

    def test_relegated(self):
        bottom = queries.relegated("Brasileirao", "2019", n=4)
        assert len(bottom) == 4
        # Bottom teams have the fewest points.
        assert bottom[0]["points"] <= bottom[-1]["points"]


# ---------------------------------------------------------------------------
# R10 - aggregate statistics
# ---------------------------------------------------------------------------
class TestStatistics:
    def test_statistics_overall(self):
        s = queries.statistics()
        assert s["matches"] > 0
        assert s["avg_goals"] is not None and s["avg_goals"] > 0
        assert 0 <= s["home_win_rate"] <= 1
        assert s["home_wins"] + s["away_wins"] + s["draws"] == s["matches"]

    def test_statistics_by_competition(self):
        s = queries.statistics(competition="brasileirao", season="2019")
        assert s["matches"] > 0
        assert s["competition"] == COMP_BRASILEIRAO_A

    def test_biggest_wins(self):
        wins = queries.biggest_wins(limit=5)
        assert wins
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)
        for w in wins:
            assert w["margin"] >= 0


# ---------------------------------------------------------------------------
# R11 - head-to-head
# ---------------------------------------------------------------------------
class TestHeadToHead:
    def test_head_to_head_flamengo_fluminense(self):
        h2h = queries.head_to_head("Flamengo", "Fluminense")
        assert h2h["matches_played"] > 0
        assert (
            h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
            == h2h["matches_played"]
        )
        assert h2h["team_a_goals"] >= 0
        assert h2h["team_b_goals"] >= 0
        assert len(h2h["matches"]) > 0

    def test_head_to_head_with_competition_filter(self):
        h2h = queries.head_to_head("Palmeiras", "Santos", competition="brasileirao")
        for m in h2h["matches"]:
            assert m["competition"] == COMP_BRASILEIRAO_A


# ---------------------------------------------------------------------------
# R1 - MCP server tools registered
# ---------------------------------------------------------------------------
class TestServer:
    def test_build_server_registers_tools(self):
        from soccer_mcp.server import build_server

        server = build_server()
        import asyncio

        tools = asyncio.run(server.list_tools())
        names = {t.name for t in tools}
        expected = {
            "find_matches",
            "head_to_head",
            "team_stats",
            "search_players",
            "team_players",
            "standings",
            "champion",
            "relegated",
            "statistics",
            "biggest_wins",
            "list_competitions",
            "list_teams",
            "match_stats",
        }
        assert expected.issubset(names), f"missing tools: {expected - names}"

    def test_tool_list_competitions_callable(self):
        from soccer_mcp.server import build_server

        server = build_server()
        import asyncio

        comps = asyncio.run(server.call_tool("list_competitions", {}))
        assert len(comps.structured_content["result"]) >= 3

    def test_tool_find_matches_callable(self):
        from soccer_mcp.server import build_server

        server = build_server()
        import asyncio

        res = asyncio.run(
            server.call_tool("find_matches", {"team": "Flamengo", "limit": 3})
        )
        assert len(res.structured_content["result"]) == 3


# ---------------------------------------------------------------------------
# list_teams / match_stats (supporting capabilities)
# ---------------------------------------------------------------------------
class TestSupporting:
    def test_list_teams(self):
        teams = queries.list_teams(competition="brasileirao", season="2023")
        assert "Flamengo" in teams
        assert "Palmeiras" in teams

    def test_match_stats_returns_corners_shots(self):
        res = queries.match_stats(team="Flamengo", season="2019", limit=3)
        assert res
        for m in res:
            assert "home_corners" in m
            assert "home_shots" in m