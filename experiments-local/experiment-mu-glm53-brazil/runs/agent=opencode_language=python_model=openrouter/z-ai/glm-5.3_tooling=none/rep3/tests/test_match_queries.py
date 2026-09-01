"""
BDD GWT scenarios: match queries.

Gherkin counterpart: ``tests/features/match_queries.feature``.

Covers TASK.md "Required Capabilities" -> "1. Match Queries" and the two
Gherkin sketches in "Testing Approach".
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import service as svc


class TestFindMatchesBetweenTwoTeams:
    """Scenario: Find matches between two teams (TASK.md Testing Approach)."""

    def test_given_match_data_when_search_flamengo_and_fluminense_then_listed(self, dataset):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = svc.search_matches(dataset, team="Flamengo", opponent="Fluminense")
        # Then I should receive a list of matches
        assert result["total_matches"] == 44
        assert result["returned"] > 0

    def test_given_head_to_head_matches_when_listed_then_each_has_date_score_competition(self, dataset):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = svc.search_matches(dataset, team="Flamengo", opponent="Fluminense", limit=50)
        # Then each match should have date, scores, and competition
        for m in result["matches"]:
            assert m["date"] is not None
            assert m["score"] and "-" in m["score"]
            assert m["home_goals"] is not None and m["away_goals"] is not None
            assert m["competition"] in {
                "Brasileirão Serie A",
                "Brasileirão Serie B",
                "Brasileirão Serie C",
                "Copa do Brasil",
                "Copa Libertadores",
            }

    def test_given_a_derby_when_searched_then_both_home_orders_found(self, dataset):
        # Given Fla-Flu fixtures alternate home advantage
        # When searching without venue bias
        # Then matches appear with Flamengo home and away
        result = svc.search_matches(dataset, team="Flamengo", opponent="Fluminense", limit=500)
        homes = {m["home_team"] for m in result["matches"]}
        assert "Flamengo" in homes and "Fluminense" in homes


class TestMatchFilters:
    def test_given_team_and_season_when_searched_then_only_that_season(self, dataset):
        # Given Palmeiras' 2023 season (Serie A + cups)
        # When searching matches for Palmeiras in 2023
        result = svc.search_matches(dataset, team="Palmeiras", season=2023)
        # Then every match is from 2023 and involves Palmeiras
        assert result["total_matches"] == 43
        assert all(m["season"] == 2023 for m in result["matches"])

    def test_given_competition_filter_when_searched_then_single_competition(self, dataset):
        # Given the Copa do Brasil
        # When searching Flamengo matches in that competition
        result = svc.search_matches(dataset, team="Flamengo", competition="Copa do Brasil")
        # Then only Copa do Brasil fixtures are returned
        assert result["total_matches"] > 0
        assert all(m["competition"] == "Copa do Brasil" for m in result["matches"])

    def test_given_a_date_range_when_searched_then_dates_within(self, dataset):
        # Given May 2019
        # When searching Brasileirão matches in that window
        result = svc.search_matches(
            dataset,
            competition="Brasileirão Serie A",
            date_from="2019-05-01",
            date_to="2019-05-31",
        )
        # Then all returned matches fall inside the range
        assert result["total_matches"] > 0
        for m in result["matches"]:
            assert "2019-05-01" <= m["date"] <= "2019-05-31"

    def test_given_libertadores_stage_when_searched_then_finals_only(self, dataset):
        # Given Libertadores 'final' stage matches
        # When searching with stage='final'
        result = svc.search_matches(dataset, competition="Copa Libertadores", stage="final")
        # Then only finals are returned: 2013-2018 two-legged, 2019-2020
        # single matches, plus the unscored 2022 final row (14 scored + 1 N/A)
        assert result["total_matches"] == 15
        assert all(m["stage"] == "final" for m in result["matches"])
        unscored = [m for m in result["matches"] if m["score"] == "N/A"]
        assert len(unscored) == 1
        assert {unscored[0]["home_team"], unscored[0]["away_team"]} == {"Flamengo", "Athletico Paranaense"}

    def test_given_limit_when_searched_then_pagination_fields(self, dataset):
        # Given a broad query
        # When limiting results to 5
        result = svc.search_matches(dataset, competition="Brasileirão Serie A", limit=5)
        # Then the response reports totals and truncation
        assert result["returned"] == 5
        assert result["truncated"] is True
        assert result["total_matches"] > 5

    def test_given_unknown_team_when_searched_then_helpful_error(self, dataset):
        # Given a team that matches nothing at all
        # When searching
        # Then a descriptive ValueError is raised
        with pytest.raises(ValueError, match="No team matching"):
            svc.search_matches(dataset, team="Honolulu United")

    def test_given_a_known_club_without_matches_when_searched_then_empty(self, dataset):
        # Given Real Madrid exists via FIFA players but played no matches
        # When searching its matches
        # Then an empty (not erroneous) response is returned
        result = svc.search_matches(dataset, team="Real Madrid")
        assert result["total_matches"] == 0
        assert result["matches"] == []

    def test_given_unknown_competition_when_searched_then_helpful_error(self, dataset):
        with pytest.raises(ValueError, match="Unknown competition"):
            svc.search_matches(dataset, competition="La Liga")

    def test_given_unparseable_date_when_searched_then_error(self, dataset):
        with pytest.raises(ValueError, match="date_from"):
            svc.search_matches(dataset, date_from="yesterday")


class TestLastMatch:
    def test_given_two_teams_when_last_match_requested_then_most_recent(self, dataset):
        # Given "When did Flamengo last play Corinthians?"
        # When requesting the last match
        result = svc.last_match(dataset, "Flamengo", "Corinthians")
        # Then the most recent fixture is returned with a score
        m = result["last_match"]
        assert m["date"] == "2023-10-08"
        assert m["home_team"] == "Corinthians"
        assert m["score"] == "1-1"

    def test_given_a_team_when_last_match_requested_then_any_opponent(self, dataset):
        result = svc.last_match(dataset, "Palmeiras")
        assert result["last_match"] is not None
        assert result["last_match"]["season"] == 2023


class TestDerbies:
    def test_given_2023_when_derbies_requested_then_rivalries_found(self, dataset):
        # Given "Show me all derbies in 2023"
        # When requesting derby matches for 2023
        result = svc.derby_matches(dataset, season=2023)
        # Then the classic rivalries appear with their fixtures
        by_name = {d["derby"]: d["total_matches"] for d in result["derbies"]}
        assert by_name["Fla-Flu"] == 4  # league double header + cup semifinal legs
        assert by_name["Gre-Nal (Grêmio x Internacional)"] == 2
        assert by_name["Choque-Rei (Palmeiras x São Paulo)"] == 4

    def test_given_derby_when_restricted_then_competition_filter(self, dataset):
        result = svc.derby_matches(dataset, season=2023, competition="Copa do Brasil")
        assert all(m["competition"] == "Copa do Brasil" for d in result["derbies"] for m in d["matches"])


class TestHeadToHead:
    def test_given_fluflu_when_compared_then_summary_counts(self, dataset):
        # Given "Compare Palmeiras and Santos head-to-head" style questions
        # When requesting Flamengo vs Fluminense history
        h2h = svc.head_to_head(dataset, "Flamengo", "Fluminense")
        # Then the summary reports wins/draws/losses and goals for both sides
        s = h2h["summary"]
        assert s["matches"] == 44
        assert s["Flamengo wins"] == 18
        assert s["Fluminense wins"] == 14
        assert s["draws"] == 12
        assert s["Flamengo goals"] == 60
        assert s["Fluminense goals"] == 48

    def test_given_head_to_head_when_filtered_then_single_season(self, dataset):
        h2h = svc.head_to_head(dataset, "Palmeiras", "Santos", competition="Brasileirão Serie A", season=2019)
        # Palmeiras and Santos met twice in the 2019 league
        assert h2h["summary"]["matches"] == 2

    def test_given_same_team_twice_when_compared_then_error(self, dataset):
        with pytest.raises(ValueError, match="same club"):
            svc.head_to_head(dataset, "Flamengo", "Flamengo-RJ")
