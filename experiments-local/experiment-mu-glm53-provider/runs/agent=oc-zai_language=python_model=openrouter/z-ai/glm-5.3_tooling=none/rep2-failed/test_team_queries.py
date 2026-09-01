"""BDD scenarios for team queries (TASK.md "Team Queries").

Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

from data_loader import SERIE_A
from server import get_best_records, get_head_to_head, get_team_stats
from stats import team_record


class TestTeamStatistics:
    """Gherkin: 'What is Corinthians' home record in 2022?'"""

    def test_statistics_include_wins_draws_losses_and_goals(self, data):
        """
        Scenario: Get team statistics
          Given the match data is loaded
          When I request statistics for "Palmeiras" in season "2023"
          Then I should receive wins, losses, draws, and goals
        """
        result = get_team_stats(team="Palmeiras", competition="Brasileirão", season=2023)
        record = result["data"]
        assert record["matches"] > 0
        for field in ("wins", "draws", "losses", "goals_for", "goals_against"):
            assert isinstance(record[field], int)
        assert record["wins"] + record["draws"] + record["losses"] == record["matches"]

    def test_corinthians_home_record_2022(self, data):
        """
        Scenario: home-only record
          Given Corinthians' 2022 Brasileirão matches
          When I request their home record
          Then only home matches are counted (19 in a full season)
        """
        result = get_team_stats(
            team="Corinthians", competition="Brasileirão", season=2022, venue="home"
        )
        assert result["data"]["home"]["matches"] == 19
        assert result["data"]["away"]["matches"] == 0
        assert result["data"]["matches"] == 19

    def test_home_and_away_lines_partition_the_record(self, data):
        """
        Scenario: home/away split
          Given any team season
          When the record is computed
          Then home matches plus away matches equal total matches
        """
        result = get_team_stats(team="Flamengo", competition="Brasileirão", season=2019)
        record = result["data"]
        assert record["home"]["matches"] + record["away"]["matches"] == record["matches"]
        assert record["home"]["matches"] == 19

    def test_2019_flamengo_record_matches_history(self, data):
        """
        Scenario: record verified against real history
          Given the 2019 Brasileirão
          When Flamengo's record is computed
          Then it is 28 wins, 6 draws, 4 losses (champions with 90 points)
        """
        matches = data.matches_by_competition(SERIE_A, 2019)
        record = team_record(data.matches_for_team("flamengo-rj"), "flamengo-rj")
        flamengo_2019 = [m for m in matches if m.involves("flamengo-rj")]
        record = team_record(flamengo_2019, "flamengo-rj")
        assert (record.wins, record.draws, record.losses) == (28, 6, 4)
        assert record.points == 90


class TestHeadToHead:
    """Gherkin: 'Compare Palmeiras and Santos head-to-head'."""

    def test_palmeiras_santos_head_to_head(self, data):
        """
        Scenario: head-to-head comparison
          Given Palmeiras and Santos have met many times
          When I compare them head-to-head
          Then wins, draws, losses, goals and meetings are reported
        """
        result = get_head_to_head("Palmeiras", "Santos")
        payload = result["data"]
        assert payload["total_meetings"] > 30
        assert (
            payload["team_a_wins"] + payload["team_b_wins"] + payload["draws"]
            == payload["total_meetings"]
        )
        assert payload["matches"], "meeting list must not be empty"

    def test_head_to_head_respects_competition_filter(self, data):
        """
        Scenario: filtered head-to-head
          Given the Fla-Flu derby
          When compared only in Copa do Brasil
          Then fewer meetings are reported than overall
        """
        overall = get_head_to_head("Flamengo", "Fluminense")
        cup_only = get_head_to_head("Flamengo", "Fluminense", competition="Copa do Brasil")
        assert 0 < cup_only["data"]["total_meetings"] < overall["data"]["total_meetings"]

    def test_head_to_head_between_teams_that_never_met(self, data):
        """
        Scenario: no meetings
          Given two teams from different eras/competitions
          When compared head-to-head
          Then a graceful "no matches" answer is returned
        """
        result = get_head_to_head("Flamengo", "Nacional (URU)")
        assert result["data"]["total_meetings"] == 0


class TestBestRecords:
    """Gherkin: 'Which team has the best home record?' / 'best away record?'."""

    def test_best_home_record_in_serie_a(self, data):
        """
        Scenario: best home record
          Given all Brasileirão matches
          When teams are ranked by points with venue "home"
          Then a ranking is returned led by a major club
        """
        result = get_best_records(competition="Brasileirão", venue="home", limit=5)
        ranking = result["data"]["ranking"]
        assert len(ranking) == 5
        points = [row["points"] for row in ranking]
        assert points == sorted(points, reverse=True)

    def test_best_away_record_in_serie_a_2023(self, data):
        """
        Scenario: best away record for a season
          Given the 2023 Brasileirão
          When teams are ranked by win rate with venue "away"
          Then the leader has more away wins than losses
        """
        result = get_best_records(
            competition="Serie A", season=2023, metric="win_rate", venue="away", limit=3
        )
        leader = result["data"]["ranking"][0]
        assert leader["away"]["wins"] > leader["away"]["losses"]
        assert leader["matches"] <= 19

    def test_top_scoring_teams_2023(self, data):
        """
        Scenario: 'Which team scored the most goals in Serie A 2023?'
          Given the 2023 Brasileirão
          When teams are ranked by goals
          Then the ranking is sorted by goals scored
        """
        result = get_best_records(competition="Serie A", season=2023, metric="goals", limit=5)
        goals = [row["goals_for"] for row in result["data"]["ranking"]]
        assert goals == sorted(goals, reverse=True)
        assert goals[0] >= 55
