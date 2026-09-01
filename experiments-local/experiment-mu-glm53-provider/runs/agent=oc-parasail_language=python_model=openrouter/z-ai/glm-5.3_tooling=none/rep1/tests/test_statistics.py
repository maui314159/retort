"""Feature: Statistical Analysis
  Aggregate statistics: goals per match, home vs away performance,
  head-to-head records, biggest wins and derby fixtures.
"""

import pytest

from brazilian_soccer import queries
from brazilian_soccer.queries import QueryError


class TestGoalsAndRates:
    def test_average_goals_per_match_in_the_brasileirao(self, repo):
        # Given all curated Serie A matches
        summary = queries.stats_summary(repo, competition="Brasileirão Serie A")
        # When aggregated
        # Then goals per match, home advantage and extremes are reported
        assert summary["matches"] == 8321
        assert summary["average_goals_per_match"] == pytest.approx(2.57, abs=0.01)
        assert summary["home_win_rate"] == pytest.approx(0.497, abs=0.005)
        assert summary["home_win_rate"] > summary["away_win_rate"]
        assert summary["home_wins"] + summary["away_wins"] + summary["draws"] == summary["matches"]

    def test_season_comparison_2018_vs_2019(self, repo):
        # Given the 2018 and 2019 Brasileirão seasons
        # When both are summarised
        s2018 = queries.stats_summary(repo, competition="serie a", season=2018)
        s2019 = queries.stats_summary(repo, competition="serie a", season=2019)
        # Then each is a complete season and the comparison is possible
        for summary in (s2018, s2019):
            assert summary["matches"] == 380
            assert 1.5 < summary["average_goals_per_match"] < 3.5
            assert summary["date_range"][0].startswith(str(summary["season"]))

    def test_summary_includes_biggest_win(self, repo):
        summary = queries.stats_summary(repo, competition="libertadores", season=2019)
        assert summary["biggest_win"]["margin"] >= 2
        assert summary["teams"] > 10


class TestHeadToHead:
    def test_totals_are_consistent(self, repo):
        # Given the Fla-Flu derby across all competitions
        result = queries.head_to_head(repo, "Flamengo", "Fluminense")
        # When the record is computed
        # Then wins, draws and losses add up to matches played
        played = result["matches_played"]
        assert (
            result["team_a_wins"] + result["team_b_wins"] + result["draws"] == played
        )
        assert result["team_a_wins"] == 18
        assert result["team_b_wins"] == 14
        assert result["draws"] == 12

    def test_head_to_head_within_one_competition(self, repo):
        # Given Palmeiras vs Santos in the Brasileirão only
        result = queries.head_to_head(
            repo, "Palmeiras", "Santos", competition="serie a"
        )
        # When restricted to one competition
        # Then only league meetings are counted
        assert result["matches_played"] > 20
        assert all(
            m["competition"] == "Brasileirão Serie A" for m in result["matches"]
        )

    def test_head_to_head_requires_two_different_teams(self, repo):
        with pytest.raises(QueryError):
            queries.head_to_head(repo, "Flamengo", "Flamengo")


class TestBiggestWins:
    def test_biggest_wins_overall(self, repo):
        # Given all curated matches
        result = queries.biggest_wins(repo, limit=5)
        # When ranked by margin
        # Then the top of the list has the largest margins
        margins = [win["margin"] for win in result["biggest_wins"]]
        assert margins[0] == 8
        assert margins == sorted(margins, reverse=True)
        assert result["biggest_wins"][0]["winner"] is not None

    def test_biggest_win_in_a_season(self, repo):
        # Given the 2019 Brasileirão
        result = queries.biggest_wins(repo, competition="serie a", season=2019, limit=3)
        # When ranked
        # Then Flamengo's 6-1 win over Avaí is among the top victories
        matches = result["biggest_wins"]
        assert matches[0]["margin"] >= matches[1]["margin"]
        flamengo_win = next(
            (
                win
                for win in matches
                if win["home_team"] == "Flamengo" and win["home_goals"] == 6
            ),
            None,
        )
        assert flamengo_win is not None
        assert flamengo_win["away_team"] == "Avai"

    def test_biggest_wins_respond_for_every_competition(self, repo):
        for competition in ["serie a", "serie b", "serie c", "copa do brasil", "libertadores"]:
            result = queries.biggest_wins(repo, competition=competition, limit=3)
            assert result["biggest_wins"]

    def test_no_matches_raises_helpful_error(self, repo):
        with pytest.raises(QueryError, match="No matches found"):
            queries.biggest_wins(repo, competition="serie b", season=2013)


class TestDerbies:
    def test_derbies_in_a_season(self, repo):
        # Given the 2023 season
        result = queries.derby_matches(repo, season=2023)
        # When traditional rivals' meetings are listed
        # Then only derby fixtures are returned, each named
        assert result["total_matches"] == 28
        derby_names = {match["derby"] for match in result["derbies"]}
        assert len(derby_names) > 1
        for match in result["derbies"]:
            assert match["season"] == 2023

    def test_derbies_2019_include_named_rivalries(self, repo):
        # Given the 2019 season
        result = queries.derby_matches(repo, season=2019)
        # When listed
        # Then classic rivalries appear by name
        names = {match["derby"] for match in result["derbies"]}
        assert {"Fla-Flu", "Grenal", "Derby Paulista"} <= names

    def test_grenal_fixture_content(self, repo):
        # Given the Grenal derby
        result = queries.derby_matches(repo, season=2019)
        grenais = [
            m for m in result["derbies"] if m["derby"] == "Grenal"
        ]
        # When the 2019 fixtures are inspected
        # Then they really are Grêmio vs Internacional matches
        assert grenais
        for match in grenais:
            teams = {match["home_team"], match["away_team"]}
            assert teams == {"Grêmio", "Internacional"}
