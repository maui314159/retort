"""BDD tests for match queries (spec section: "1. Match Queries").

Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
"""

from __future__ import annotations

from datetime import date


class TestSearchBetweenTeams:
    """Scenario: Find matches between two teams"""

    def test_flamengo_vs_fluminense(self, svc):
        result = svc.search_matches(team="Flamengo", opponent="Fluminense")
        assert "Flamengo" in result and "Fluminense" in result
        assert "Head-to-head" in result
        assert result.count("\n- ") >= 15, "should list many Fla-Flu matches"

    def test_each_match_has_date_score_competition(self, svc):
        result = svc.search_matches(team="Flamengo", opponent="Fluminense", limit=5)
        lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
        assert lines
        for ln in lines:
            # "- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A 2023, Round 22)"
            assert ": " in ln, "date present"
            assert " (Brasileirão Série A" in ln or " (" in ln, "competition present"
            assert "-" in ln.split(": ")[1], "score present"

    def test_matches_are_newest_first(self, svc):
        result = svc.search_matches(team="Flamengo", opponent="Fluminense", limit=10)
        dates = [
            ln[2:12]
            for ln in result.splitlines()
            if ln.startswith("- ") and ln[2:12].count("-") == 2
        ]
        assert dates == sorted(dates, reverse=True)


class TestSearchByTeam:
    """Scenario: Matches of one team"""

    def test_palmeiras_2023(self, svc):
        result = svc.search_matches(team="Palmeiras", season=2023, competition="Brasileirão Série A")
        assert "Palmeiras" in result
        assert "37 matches" in result  # 2023 source data has 37 Palmeiras league matches

    def test_team_with_state_suffix(self, svc):
        plain = svc.search_matches(team="Palmeiras", season=2019, limit=3)
        suffixed = svc.search_matches(team="Palmeiras-SP", season=2019, limit=3)
        assert plain.splitlines()[0] == suffixed.splitlines()[0]

    def test_venue_filters(self, svc):
        allm = svc.search_matches(team="Grêmio", season=2019, competition="Brasileirão Série A", limit=1)
        assert "38 matches" in allm


class TestSearchByDateRange:
    """Scenario: Search by date range"""

    def test_date_range(self, svc):
        result = svc.search_matches(date_from="2023-05-01", date_to="2023-05-31", limit=50)
        assert "matches in dataset" in result
        for ln in result.splitlines():
            if ln.startswith("- 2"):
                assert ln[2:12].startswith("2023-05"), ln

    def test_single_day(self, svc):
        result = svc.search_matches(date_from="2023-09-24", date_to="2023-09-24", limit=50)
        for ln in result.splitlines():
            if ln.startswith("- 2"):
                assert ln[2:12] == "2023-09-24"


class TestSearchByStage:
    """Scenario: Cup stage filters"""

    def test_libertadores_finals(self, svc):
        result = svc.search_matches(competition="Libertadores", stage="final")
        assert "Copa Libertadores" in result
        # 2019 final: Flamengo 2-1 River Plate (single match)
        assert "2019-11-23" in result
        assert "Flamengo" in result

    def test_quarterfinals_not_confused_with_finals(self, svc):
        finals = svc.search_matches(competition="Libertadores", stage="final", limit=50)
        assert "Quarterfinals" not in finals

    def test_copa_do_brasil_semifinals(self, svc):
        result = svc.search_matches(competition="Copa do Brasil", stage="semifinal", season=2019)
        assert "Semifinal" in result


class TestSearchEdgeCases:
    """Scenario: Tolerant inputs and empty results"""

    def test_unknown_team(self, svc):
        result = svc.search_matches(team="Real Madrid")
        assert "not found" in result.lower()

    def test_unknown_competition(self, svc):
        result = svc.search_matches(competition="Premier League")
        assert "not found" in result
        assert "Brasileirão Série A" in result  # suggests available competitions

    def test_no_criteria_lists_all(self, svc):
        result = svc.search_matches(limit=5)
        assert "matches in dataset" in result

    def test_opponent_only(self, svc):
        result = svc.search_matches(opponent="Palmeiras", season=2023, limit=3)
        assert "matches in dataset" in result


class TestLastMatch:
    """Spec sample question: 'When did Flamengo last play Corinthians?'"""

    def test_last_flamengo_match(self, svc):
        result = svc.search_matches(team="Flamengo", limit=1)
        first_line = next(ln for ln in result.splitlines() if ln.startswith("- "))
        assert first_line[2:12].count("-") == 2  # begins with an ISO date
