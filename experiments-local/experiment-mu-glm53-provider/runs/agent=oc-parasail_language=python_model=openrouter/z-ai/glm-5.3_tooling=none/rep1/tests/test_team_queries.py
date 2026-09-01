"""Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
  (plus venue splits, per-competition breakdowns and league rankings)
"""

import pytest

from brazilian_soccer import queries
from brazilian_soccer.queries import QueryError


class TestTeamStatistics:
    def test_stats_for_team_and_season(self, repo):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        stats = queries.team_stats(repo, "Palmeiras", season=2023)
        # Then I should receive wins, losses, draws, and goals
        overall = stats["overall"]
        for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
            assert field in overall
        assert overall["matches"] == 43
        assert (
            overall["wins"] + overall["draws"] + overall["losses"]
            == overall["matches"]
        )
        assert overall["points"] == 3 * overall["wins"] + overall["draws"]

    def test_corinthians_home_record(self, repo):
        # Given Corinthians' 2019 Brasileirão season
        stats = queries.team_stats(
            repo, "Corinthians", season=2019, competition="serie a"
        )
        # When the home record is requested
        home = stats["home"]
        # Then it is a full 19-match home campaign with consistent totals
        assert home["matches"] == 19
        assert home["wins"] == 10
        assert home["draws"] == 7
        assert home["losses"] == 2
        assert home["goals_for"] == 25
        assert home["goals_against"] == 13
        assert home["win_rate"] == pytest.approx(10 / 19, abs=0.01)

    def test_home_and_away_splits_sum_to_overall(self, repo):
        # Given any team-season
        stats = queries.team_stats(
            repo, "Flamengo", season=2019, competition="serie a"
        )
        # When splits are computed
        overall, home, away = stats["overall"], stats["home"], stats["away"]
        # Then home plus away equals the overall record
        assert home["matches"] + away["matches"] == overall["matches"]
        assert home["wins"] + away["wins"] == overall["wins"]
        assert home["goals_for"] + away["goals_for"] == overall["goals_for"]

    def test_breakdown_by_competition(self, repo):
        # Given Palmeiras' full match history
        stats = queries.team_stats(repo, "Palmeiras")
        # When broken down by competition
        competitions = {
            entry["competition"]: entry for entry in stats["by_competition"]
        }
        # Then Palmeiras appears in every competition in the datasets
        assert set(competitions) == {
            "Brasileirão Serie A",
            "Copa do Brasil",
            "Copa Libertadores",
        }
        assert competitions["Brasileirão Serie A"]["matches"] > 700

    def test_ambiguous_team_name_raises_with_options(self, repo):
        # Given the ambiguous name "America"
        # When statistics are requested
        # Then a helpful error lists both clubs
        with pytest.raises(QueryError) as excinfo:
            queries.team_stats(repo, "America")
        message = str(excinfo.value)
        assert "America MG" in message and "America RN" in message

    def test_state_suffix_disambiguates(self, repo):
        # Given the disambiguated spelling "America-MG"
        stats = queries.team_stats(repo, "America-MG")
        # When statistics are requested
        # Then exactly one club answers
        assert stats["team"] == "America MG"
        assert stats["overall"]["matches"] > 200


class TestTeamRankings:
    def test_best_away_record_all_time(self, repo):
        # Given all curated matches
        ranking = queries.team_rankings(repo, metric="away_points", limit=5)
        # When ranked by away points
        # Then Flamengo leads with 486 points (tied with Cruzeiro, broken
        # by the overall-points tiebreak) and the list is properly ordered
        assert ranking["rankings"][0]["away_points"] == 486
        assert ranking["rankings"][0]["team"] in {"Flamengo", "Cruzeiro"}
        away_points = [row["away_points"] for row in ranking["rankings"]]
        assert away_points == sorted(away_points, reverse=True)
        teams = {row["team"] for row in ranking["rankings"]}
        assert {"Flamengo", "Cruzeiro", "São Paulo"} <= teams

    def test_most_goals_in_a_season(self, repo):
        # Given the 2019 Brasileirão
        ranking = queries.team_rankings(
            repo, competition="serie a", season=2019, metric="goals_for", limit=5
        )
        # When ranked by goals scored
        # Then champion Flamengo also had the best attack
        assert ranking["rankings"][0]["team"] == "Flamengo"
        assert ranking["rankings"][0]["goals_for"] == 86

    def test_best_home_win_rate_2019(self, repo):
        ranking = queries.team_rankings(
            repo, competition="serie a", season=2019, metric="home_win_rate", limit=3
        )
        assert ranking["rankings"][0]["home_win_rate"] >= ranking["rankings"][1]["home_win_rate"]

    def test_unknown_metric_raises(self, repo):
        with pytest.raises(QueryError, match="Unknown metric"):
            queries.team_rankings(repo, metric="flair")


class TestFindTeam:
    def test_find_team_resolves_spellings(self, repo):
        # Given several spellings of the same club
        for spelling in ["Palmeiras-SP", "palmeiras", "SE Palmeiras"]:
            # When resolved through find_team
            result = queries.find_team(repo, spelling)
            # Then one entity is returned with match counts
            assert len(result["results"]) == 1
            entity = result["results"][0]
            assert entity["key"] == "palmeiras"
            assert entity["matches_in_dataset"] > 700
            assert "Brasileirão Serie A" in entity["competitions"]

    def test_find_team_lists_disambiguations(self, repo):
        # Given the ambiguous name "Atletico"
        result = queries.find_team(repo, "Atletico")
        # When resolved
        # Then the state clubs are listed separately
        keys = {entity["key"] for entity in result["results"]}
        assert {"atletico mg", "atletico go", "atletico pr"} <= keys

    def test_find_team_reports_player_links(self, repo):
        # Given a club present in both match and player data
        result = queries.find_team(repo, "Atlético Mineiro")
        # When resolved
        # Then the entity links to its FIFA players (cross-file join)
        entity = result["results"][0]
        assert entity["key"] == "atletico mg"
        assert entity["matches_in_dataset"] > 800
        assert entity["players_in_fifa_dataset"] == 20

    def test_find_team_unknown_name_raises(self, repo):
        with pytest.raises(QueryError):
            queries.find_team(repo, "Bora Bora United")
