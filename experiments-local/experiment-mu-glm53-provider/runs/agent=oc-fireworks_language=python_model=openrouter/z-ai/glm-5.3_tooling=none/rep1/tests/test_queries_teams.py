"""
Feature: Team Queries
  As a soccer fan I want team records, venue splits, head-to-head
  comparisons and club profiles, so I can compare clubs across
  competitions and seasons.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    best_records,
    head_to_head,
    team_profile,
    team_stats,
)


class TestTeamStats:
    """TASK.md: "What is Corinthians' home record in 2022?"."""

    def test_home_record_2022(self, ds):
        """
        Scenario: Get team statistics
          Given the match data is loaded
          When I request home statistics for "Corinthians" in season "2022"
          Then I should receive matches, wins, losses, draws and goals
        """
        result = team_stats(
            ds, "Corinthians", season=2022, competition="serie_a", venue="home"
        )
        assert result["ok"], result
        record = result["record"]
        assert record["matches"] == 19
        assert record["wins"] == 12
        assert record["draws"] == 4
        assert record["losses"] == 3
        assert record["goals_for"] == 24
        assert record["goals_against"] == 11
        assert record["win_rate"] == 63.2

    def test_venue_splits_come_with_overall(self, ds):
        """
        Scenario: the default view splits home and away
          Given the match data is loaded
          When I request Corinthians' 2022 Série A record with venue "all"
          Then overall, home and away records are all returned
          And home wins plus away wins equal total wins
        """
        result = team_stats(ds, "Corinthians", season=2022, competition="serie_a")
        assert result["ok"]
        overall = result["record"]
        home = result["home_record"]
        away = result["away_record"]
        assert overall["matches"] == home["matches"] + away["matches"] == 38
        assert overall["wins"] == home["wins"] + away["wins"]

    def test_away_record_all_competitions(self, ds):
        """
        Scenario: away record across every competition
          Given the match data is loaded
          When I request Santos' away record with no scope filters
          Then the record covers more than one competition
          And a per-competition breakdown is included
        """
        result = team_stats(ds, "Santos", venue="away")
        assert result["ok"]
        assert result["record"]["matches"] > 150
        assert len(result["by_competition"]) >= 2

    def test_stats_ignore_unplayed_fixtures(self, ds):
        """
        Scenario: unplayed fixtures never inflate statistics
          Given the match data is loaded
          When I request Chapecoense's 2016 Série A record
          Then only played matches are counted
        """
        result = team_stats(ds, "Chapecoense", season=2016, competition="serie_a")
        assert result["ok"]
        assert (
            result["record"]["matches"]
            == result["record"]["wins"]
            + result["record"]["draws"]
            + result["record"]["losses"]
        )


class TestTeamProfile:
    """TASK.md: "What competitions has Palmeiras played in?"."""

    def test_palmeiras_profile(self, ds):
        """
        Scenario: a club's whole footprint in the knowledge graph
          Given the match data is loaded
          When I request the profile for "Palmeiras"
          Then I see Série A, Copa do Brasil and Libertadores
          And the all-time record and spelling variations
        """
        result = team_profile(ds, "Palmeiras")
        assert result["ok"], result
        club = result["club"]
        assert club["key"] == "palmeiras|SP"
        assert club["state"] == "SP"
        assert set(club["competitions"]) == {
            "serie_a",
            "copa_do_brasil",
            "libertadores",
        }
        assert "Palmeiras-SP" in club["name_variations"]
        record = result["all_time_record"]
        assert record["matches"] == 888
        assert record["wins"] == 422
        by_comp = {entry["competition"] for entry in result["by_competition"]}
        assert by_comp == {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"}

    def test_profile_crosses_into_player_data(self, ds):
        """
        Scenario: cross-file knowledge (matches + FIFA players)
          Given the match data is loaded
          When I request the profile for "Grêmio"
          Then the FIFA player count for the club is included
        """
        result = team_profile(ds, "Grêmio")
        assert result["ok"]
        assert result["fifa_players_in_dataset"] == 20

    def test_profile_lists_similar_clubs(self, ds):
        """
        Scenario: similarly named clubs are surfaced
          Given the match data is loaded
          When I request the profile for "Botafogo"
          Then the other Botafogos (SP, PB) are listed
        """
        result = team_profile(ds, "Botafogo")
        assert result["ok"]
        assert result["club"]["key"] == "botafogo|RJ"
        assert len(result["similar_named_clubs"]) >= 2


class TestHeadToHead:
    """TASK.md: "Compare Palmeiras and Santos head-to-head"."""

    def test_head_to_head_record(self, ds):
        """
        Scenario: head-to-head between two teams
          Given the match data is loaded
          When I compare "Palmeiras" and "Santos"
          Then I receive wins, draws and goals for both sides
          And the fixture list
        """
        result = head_to_head(ds, "Palmeiras", "Santos")
        assert result["ok"], result
        assert result["meetings"] == 41
        assert result["wins_team_a"] == 17
        assert result["draws"] == 8
        assert result["wins_team_b"] == 16
        assert result["goals_team_a"] > result["goals_team_b"]
        assert len(result["matches"]) == 20  # default limit

    def test_head_to_head_scoped_to_one_season(self, ds):
        """
        Scenario: head-to-head within one season
          Given the match data is loaded
          When I compare Flamengo and Fluminense in the 2023 season
          Then only the four 2023 meetings are counted
        """
        result = head_to_head(ds, "Flamengo", "Fluminense", season=2023)
        assert result["ok"]
        assert result["total"] == 4
        assert result["meetings"] == 4

    def test_head_to_head_reverse_orientation(self, ds):
        """
        Scenario: the order of teams only changes the perspective
          Given the match data is loaded
          When I compare Fluminense vs Flamengo
          Then the win counts mirror the Flamengo vs Fluminense view
        """
        one = head_to_head(ds, "Flamengo", "Fluminense")
        two = head_to_head(ds, "Fluminense", "Flamengo")
        assert one["wins_team_a"] == two["wins_team_b"]
        assert one["wins_team_b"] == two["wins_team_a"]


class TestBestRecords:
    """TASK.md: "Which team has the best home record?" / away record."""

    def test_best_home_record(self, ds):
        """
        Scenario: rank teams by home win rate
          Given the match data is loaded
          When I rank home records in Série A (min 100 matches)
          Then Grêmio leads with about 59%
        """
        result = best_records(
            ds, venue="home", competition="serie_a", min_matches=100, limit=5
        )
        assert result["ok"]
        top = result["records"][0]
        assert top["team"] == "Grêmio"
        assert top["win_rate"] == 59.1
        assert top["matches"] >= 100

    def test_best_away_record(self, ds):
        """
        Scenario: rank teams by away win rate
          Given the match data is loaded
          When I rank away records in Série A (min 100 matches)
          Then Cruzeiro leads with about 33%
        """
        result = best_records(
            ds, venue="away", competition="serie_a", min_matches=100, limit=5
        )
        assert result["ok"]
        top = result["records"][0]
        assert top["team"] == "Cruzeiro"
        assert top["win_rate"] == 33.0

    def test_goals_for_metric_in_one_season(self, ds):
        """
        Scenario: "Which team scored the most goals in Serie A 2023?"
          Given the match data is loaded
          When I rank 2023 Série A teams by goals_for
          Then the leader is Grêmio with 63 goals
            (2023 is covered solely by the BR-Football file)
        """
        result = best_records(
            ds,
            venue="all",
            competition="serie_a",
            season=2023,
            metric="goals_for",
            limit=3,
        )
        assert result["ok"]
        assert result["records"][0]["team"] == "Grêmio"
        assert result["records"][0]["goals_for"] == 63

    def test_metric_validation(self, ds):
        """
        Scenario: invalid metric or venue
          Given the match data is loaded
          When I rank by an unknown metric or venue
          Then a helpful error is returned
        """
        assert not best_records(ds, metric="pace")["ok"]
        assert not best_records(ds, venue="middle")["ok"]
