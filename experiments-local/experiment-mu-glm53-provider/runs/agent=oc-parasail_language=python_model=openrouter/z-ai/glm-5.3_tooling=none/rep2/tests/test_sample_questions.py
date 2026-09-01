"""End-to-end battery of sample questions answered through MCP tools.

Covers the spec's data-coverage criterion: "At least 20 sample questions
can be answered" and "Cross-file queries work (e.g. player + match data)".
Every question is dispatched through the MCP server's ``call_tool``
interface exactly as an LLM client would.
"""

from __future__ import annotations

from conftest import call_tool_sync


def answer(mcp_server, tool: str, **arguments) -> dict:
    return call_tool_sync(mcp_server, tool, arguments)


class TestMatchQuestions:
    def test_q01_flamengo_vs_fluminense_matches(self, mcp_server):
        result = answer(mcp_server, "search_matches", team="Flamengo", opponent="Fluminense", limit=10)
        assert result["total_matches"] > 30
        assert result["matches"][0]["date"]

    def test_q02_palmeiras_matches_in_2023(self, mcp_server):
        result = answer(mcp_server, "search_matches", team="Palmeiras", season=2023, limit=10)
        assert result["total_matches"] >= 37

    def test_q03_copa_do_brasil_finals(self, mcp_server):
        result = answer(mcp_server, "competition_finals", competition="Copa do Brasil")
        assert any(f["season"] == 2019 for f in result["finals"])

    def test_q04_when_did_flamengo_last_play_corinthians(self, mcp_server):
        result = answer(
            mcp_server, "search_matches", team="Flamengo", opponent="Corinthians", limit=1
        )
        latest = result["matches"][0]
        assert latest["home_team_id"] in ("flamengo", "corinthians")
        assert latest["score"] != "not recorded"

    def test_q05_libertadores_final_2019(self, mcp_server):
        result = answer(
            mcp_server,
            "search_matches",
            competition="Libertadores",
            stage="final",
            season=2019,
        )
        assert result["total_matches"] == 1
        assert result["matches"][0]["score"] == "2-1"

    def test_q06_matches_in_june_2019(self, mcp_server):
        result = answer(
            mcp_server,
            "search_matches",
            date_from="2019-06-01",
            date_to="2019-06-30",
            limit=5,
        )
        assert result["total_matches"] > 50


class TestTeamQuestions:
    def test_q07_corinthians_home_record_2022(self, mcp_server):
        result = answer(
            mcp_server,
            "team_stats",
            team="Corinthians",
            season=2022,
            competition="Série A",
            venue="home",
        )
        assert result["record"]["matches"] == 19

    def test_q08_which_team_scored_most_goals_serie_a_2023(self, mcp_server):
        result = answer(mcp_server, "top_scoring_teams", competition="Série A", season=2023, limit=3)
        assert result["teams"][0]["goals"] > 50

    def test_q09_compare_palmeiras_and_santos(self, mcp_server):
        result = answer(mcp_server, "head_to_head", team_a="Palmeiras", team_b="Santos")
        assert result["total_matches"] > 30

    def test_q10_best_away_record(self, mcp_server):
        result = answer(mcp_server, "best_records", venue="away", minimum_matches=50, limit=3)
        assert result["ranking"]

    def test_q11_what_competitions_has_palmeiras_played_in(self, mcp_server):
        result = answer(mcp_server, "team_profile", team="Palmeiras")
        names = [entry["competition"] for entry in result["competitions"]]
        assert "Copa Libertadores" in names

    def test_q12_team_graph_for_gremio(self, mcp_server):
        result = answer(mcp_server, "team_graph", team="Grêmio")
        assert result["squad"], "cross-file query: FIFA squad for a match-data club"


class TestPlayerQuestions:
    def test_q13_who_is_neymar(self, mcp_server):
        result = answer(mcp_server, "search_players", name="Neymar")
        neymar = result["players"][0]
        assert neymar["name"] == "Neymar Jr"
        assert neymar["overall"] == 92

    def test_q14_top_brazilian_players(self, mcp_server):
        result = answer(mcp_server, "top_players", nationality="Brazil", limit=5)
        assert result["players"][0]["name"] == "Neymar Jr"

    def test_q15_players_at_gremio(self, mcp_server):
        result = answer(mcp_server, "search_players", club="Grêmio", limit=30)
        assert result["total_players"] >= 20

    def test_q16_brazilian_players_at_brazilian_clubs(self, mcp_server):
        result = answer(mcp_server, "players_at_brazilian_clubs")
        assert len(result["clubs"]) == 15

    def test_q17_brazilian_forwards_at_high_rating(self, mcp_server):
        result = answer(
            mcp_server, "search_players", nationality="Brazil", position="ST", min_overall=80
        )
        assert result["total_players"] > 0


class TestCompetitionQuestions:
    def test_q18_who_won_the_2019_brasileirao(self, mcp_server):
        result = answer(mcp_server, "standings", competition="Série A", season=2019)
        assert result["champion"]["team"] == "Flamengo (RJ)"

    def test_q19_which_teams_were_relegated_in_2020(self, mcp_server):
        result = answer(mcp_server, "standings", competition="Série A", season=2020)
        assert len(result["relegated"]) == 4

    def test_q20_libertadores_winners_by_year(self, mcp_server):
        result = answer(mcp_server, "competition_finals", competition="Libertadores")
        assert {f["season"] for f in result["finals"]} >= {2013, 2014, 2015, 2019}

    def test_q21_competition_coverage(self, mcp_server):
        result = answer(mcp_server, "competition_info")
        assert set(result["competitions"]) == {
            "serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"
        }


class TestStatisticsQuestions:
    def test_q22_average_goals_per_match_brasileirao(self, mcp_server):
        result = answer(mcp_server, "goal_averages", competition="Série A")
        assert 2.0 < result["average_goals_per_match"] < 3.0

    def test_q23_biggest_wins_in_the_dataset(self, mcp_server):
        result = answer(mcp_server, "biggest_wins", limit=5)
        assert result["matches"][0]["goal_margin"] >= 8

    def test_q24_derbies_in_2023(self, mcp_server):
        result = answer(mcp_server, "derbies", season=2023)
        assert result["total_matches"] > 10

    def test_q25_home_vs_away_performance(self, mcp_server):
        result = answer(mcp_server, "goal_averages")
        assert result["home_win_rate"] > result["away_win_rate"]


class TestGraphQuestions:
    def test_q26_graph_overview(self, mcp_server):
        result = answer(mcp_server, "graph_overview")
        assert result["nodes"] > 30000

    def test_q27_how_are_neymar_and_grêmio_connected(self, mcp_server):
        result = answer(mcp_server, "graph_paths", entity_a="Neymar", entity_b="Grêmio", max_hops=4)
        assert result["paths"] or "No connection" in result["summary"]

    def test_q28_disambiguate_team_names(self, mcp_server):
        result = answer(mcp_server, "list_clubs", query="botafogo", limit=10)
        names = [club["name"] for club in result["clubs"]]
        assert any("Botafogo" in name for name in names)


QUESTION_COUNT = 28
