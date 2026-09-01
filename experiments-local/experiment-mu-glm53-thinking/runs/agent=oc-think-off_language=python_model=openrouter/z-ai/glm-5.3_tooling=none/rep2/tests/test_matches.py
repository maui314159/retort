"""BDD scenarios for match queries (Gherkin: find matches / head-to-head)."""

import soccer.queries as q


class TestFindMatches:
    def test_matches_between_two_teams(self, data):
        """Scenario: find matches between two teams.

        Given the match data is loaded
        When I search for matches between "Flamengo" and "Fluminense"
        Then I should receive a list of matches
        And each match should have date, scores, and competition
        """
        result = q.find_matches(data, team="Flamengo", opponent="Fluminense")
        assert result["total"] > 20
        assert result["matches"]
        for m in result["matches"]:
            assert set(m) >= {"date", "home", "away", "home_goals", "away_goals", "competition"}
            assert m["date"][:4].isdigit()
            assert {"flamengo", "fluminense"} <= {m["home"], m["away"]}

    def test_matches_by_team_with_state_suffix_variant(self, data):
        """Team name variants resolve to the same team."""
        suffixed = q.find_matches(data, team="Flamengo-RJ", competition="Brasileirão")
        plain = q.find_matches(data, team="Flamengo", competition="Brasileirão")
        assert suffixed["total"] == plain["total"]
        assert plain["total"] > 0

    def test_matches_by_team_and_season(self, data):
        """When I ask for Palmeiras matches in 2023 I only get 2023."""
        result = q.find_matches(data, team="Palmeiras", season=2023)
        assert result["total"] > 0
        for m in result["matches"]:
            assert m["season"] == 2023

    def test_matches_by_competition(self, data):
        libertadores = q.find_matches(data, competition="Libertadores")
        cup = q.find_matches(data, competition="Copa do Brasil")
        assert libertadores["total"] > 1000
        assert cup["total"] > 1000
        for m in libertadores["matches"]:
            assert m["competition"] == "Copa Libertadores"

    def test_matches_by_date_range(self, data):
        result = q.find_matches(
            data, date_from="2019-11-01", date_to="2019-11-30"
        )
        assert result["total"] > 0
        for m in result["matches"]:
            assert "2019-11" in m["date"]

    def test_matches_in_cup_finals(self, data):
        """Scenario: find all Copa do Brasil finals."""
        finals = q.find_matches(
            data, competition="Copa do Brasil", stage="final"
        )
        assert finals["total"] > 0
        for m in finals["matches"]:
            assert m["round"] == "final"

    def test_stage_match_ignores_case_and_accents(self, data):
        semis = q.find_matches(data, competition="Libertadores", stage="Semifinals")
        assert semis["total"] > 20

    def test_unknown_team_returns_empty(self, data):
        assert q.find_matches(data, team="Zzzz Qqqq Xyzzy")["total"] == 0

    def test_limit_is_respected(self, data):
        result = q.find_matches(data, team="Flamengo", limit=5)
        assert result["returned"] == 5
        assert result["total"] > 5


class TestLastMatch:
    def test_most_recent_match_between_teams(self, data):
        """Scenario: when did Flamengo last play Corinthians?"""
        m = q.last_match(data, "Flamengo", "Corinthians")
        assert "error" not in m
        assert {"flamengo", "corinthians"} <= {m["home"], m["away"]}
        assert isinstance(m["home_goals"], int)

    def test_most_recent_match_of_a_team(self, data):
        m = q.last_match(data, "Flamengo")
        assert "error" not in m
        assert m["home"] == "flamengo" or m["away"] == "flamengo"


class TestHeadToHead:
    def test_head_to_head_record(self, data):
        """Scenario: compare Palmeiras and Santos head-to-head."""
        h = q.head_to_head(data, "Palmeiras", "Santos")
        assert h["total_matches"] > 20
        wins = h["Palmeiras wins"] + h["Santos wins"] + h["draws"]
        assert wins == h["total_matches"]

    def test_head_to_head_unknown_team(self, data):
        assert "error" in q.head_to_head(data, "Palmeiras", "Nonexistent FC")

    def test_head_to_head_same_team(self, data):
        assert "error" in q.head_to_head(data, "Palmeiras", "Palmeiras")
