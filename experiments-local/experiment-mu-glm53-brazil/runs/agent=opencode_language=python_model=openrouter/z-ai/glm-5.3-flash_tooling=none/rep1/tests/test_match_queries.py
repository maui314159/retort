"""Tests for match queries (R3, R4, R5)."""

from brazilian_soccer_mcp.queries import QueryEngine


class TestMatchSearch:
    def test_find_matches_between_two_teams(self, engine: QueryEngine):
        result = engine.search_matches(team="Flamengo", opponent="Fluminense")
        assert result["total_matches"] > 0
        assert result["returned"] > 0
        for match in result["matches"]:
            names = {match["home_team"], match["away_team"]}
            assert names == {"Flamengo", "Fluminense"}
        record = result["summary"]
        assert (
            record["team_a_wins"] + record["team_b_wins"] + record["draws"]
            == result["total_matches"]
        )

    def test_team_filter_matches_home_or_away(self, engine: QueryEngine):
        result = engine.search_matches(team="Palmeiras", season=2020, limit=100)
        roles = {m["home_team"] == "Palmeiras" for m in result["matches"]}
        assert roles == {True, False}, "team filter should match home and away"

    def test_opponent_only_query(self, engine: QueryEngine):
        result = engine.search_matches(opponent="Corinthians", season=2022)
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert "Corinthians" in (match["home_team"], match["away_team"])

    def test_season_filter(self, engine: QueryEngine):
        result = engine.search_matches(team="Palmeiras", season=2023, limit=100)
        assert result["total_matches"] > 0
        assert all(m["season"] == 2023 for m in result["matches"])

    def test_date_range_filter_iso(self, engine: QueryEngine):
        result = engine.search_matches(
            team="Flamengo", date_from="2023-01-01", date_to="2023-12-31", limit=100
        )
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert match["date"] is not None
            assert "2023-01-01" <= match["date"] <= "2023-12-31"

    def test_date_range_filter_brazilian_format(self, engine: QueryEngine):
        iso = engine.search_matches(
            team="Santos", date_from="2020-01-01", date_to="2020-12-31", limit=200
        )
        br = engine.search_matches(
            team="Santos", date_from="01/01/2020", date_to="31/12/2020", limit=200
        )
        assert br["total_matches"] == iso["total_matches"] > 0

    def test_competition_filter_brasileirao(self, engine: QueryEngine):
        result = engine.search_matches(team="Flamengo", competition="Brasileirão", limit=100)
        assert result["total_matches"] > 0
        assert all(m["competition"] == "Brasileirão" for m in result["matches"])

    def test_competition_filter_alias(self, engine: QueryEngine):
        for alias, canonical in (
            ("brasileirao", "Brasileirão"),
            ("serie a", "Brasileirão"),
            ("copa do brasil", "Copa do Brasil"),
            ("libertadores", "Libertadores"),
        ):
            result = engine.search_matches(competition=alias, season=2019, limit=5)
            assert result["query"]["competition"] == canonical

    def test_competition_filter_copa_do_brasil(self, engine: QueryEngine):
        result = engine.search_matches(competition="Copa do Brasil", season=2019, limit=100)
        assert result["total_matches"] > 0
        assert all(m["competition"] == "Copa do Brasil" for m in result["matches"])

    def test_team_name_variations_equivalent(self, engine: QueryEngine):
        suffixed = engine.search_matches(team="Palmeiras-SP", season=2020, limit=100)
        plain = engine.search_matches(team="Palmeiras", season=2020, limit=100)
        assert suffixed["total_matches"] == plain["total_matches"]

    def test_limit_and_pagination_note(self, engine: QueryEngine):
        limited = engine.search_matches(team="Flamengo", limit=5)
        assert limited["returned"] == 5
        assert limited["total_matches"] >= limited["returned"]
        assert limited["note"] is not None

    def test_unknown_team_returns_empty(self, engine: QueryEngine):
        result = engine.search_matches(team="FC Zenit Uruguai 9999")
        assert result["total_matches"] == 0


class TestStageAndRoundFilter:
    def test_libertadores_final_exact(self, engine: QueryEngine):
        result = engine.search_matches(
            competition="libertadores", round_or_stage="final", limit=50
        )
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert (match["stage"] or "").lower() == "final"

    def test_final_does_not_match_semifinals(self, engine: QueryEngine):
        result = engine.search_matches(
            competition="libertadores", round_or_stage="final", limit=100
        )
        stages = {(m["stage"] or "").lower() for m in result["matches"]}
        assert stages == {"final"}

    def test_round_number_filter(self, engine: QueryEngine):
        result = engine.search_matches(
            competition="Brasileirão", season=2019, round_or_stage="round 1", limit=50
        )
        assert result["total_matches"] > 0
        rounds = {m["round"] for m in result["matches"]}
        assert rounds == {"1"}


class TestBDDScenarios:
    """BDD scenarios from the specification."""

    def test_find_matches_between_two_teams(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = engine.search_matches(team="Flamengo", opponent="Fluminense", limit=100)
        # Then I should receive a list of matches
        assert len(result["matches"]) > 0
        # And each match should have date, scores, and competition
        for match in result["matches"]:
            assert match["date"]
            assert match["home_goals"] is not None
            assert match["away_goals"] is not None
            assert match["competition"]

    def test_get_team_statistics(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        result = engine.get_team_stats(team="Palmeiras", season=2023)
        record = result["record"]
        # Then I should receive wins, losses, draws, and goals
        assert record["played"] == record["wins"] + record["draws"] + record["losses"]
        assert record["goals_for"] > 0
        assert record["goals_against"] >= 0
