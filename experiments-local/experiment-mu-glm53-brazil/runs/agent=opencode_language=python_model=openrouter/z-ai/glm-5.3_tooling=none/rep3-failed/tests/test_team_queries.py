"""BDD scenarios for team queries.

Feature: Team Queries
  Users ask for a team's record, goals and head-to-head history.
"""

from __future__ import annotations

from brazilian_soccer_mcp.models import HeadToHead, TeamStats


class TestTeamSeasonRecord:
    """
    Scenario: Get team statistics for a season
      Given the match data is loaded
      When I request statistics for "Palmeiras" in season 2022
      Then I should receive wins, losses, draws, and goals
    """

    def test_when_requesting_palmeiras_2022_stats_then_the_full_record_is_returned(self, engine):
        stats = engine.team_stats("Palmeiras", season=2022, competition="Série A")
        assert isinstance(stats, TeamStats)
        assert (stats.matches, stats.wins, stats.draws, stats.losses) == (38, 23, 12, 3)
        assert (stats.goals_for, stats.goals_against) == (64, 27)

    def test_when_requesting_stats_then_wins_draws_losses_sum_to_matches(self, engine):
        for team in ("Flamengo", "Corinthians", "Grêmio", "Bahia"):
            stats = engine.team_stats(team, season=2019)
            assert stats.wins + stats.draws + stats.losses == stats.matches

    def test_when_stats_cover_home_and_away_then_they_sum_to_the_overall_record(self, engine):
        overall = engine.team_stats("Fluminense", season=2019, competition="Série A")
        home = engine.team_stats("Fluminense", season=2019, competition="Série A", venue="home")
        away = engine.team_stats("Fluminense", season=2019, competition="Série A", venue="away")
        assert home.matches + away.matches == overall.matches
        assert home.goals_for + away.goals_for == overall.goals_for


class TestTeamHomeRecord:
    """
    Scenario: What is Corinthians' home record in 2022?
      Given the match data is loaded
      When I request Corinthians home statistics for 2022
      Then I receive the home wins, draws, losses and goals
    """

    def test_when_requesting_corinthians_home_2022_then_the_record_matches_the_data(self, engine):
        stats = engine.team_stats("Corinthians", season=2022, competition="Série A", venue="home")
        assert (stats.matches, stats.wins, stats.draws, stats.losses) == (19, 12, 4, 3)
        assert (stats.goals_for, stats.goals_against) == (24, 11)
        assert stats.win_rate == 12 / 19


class TestHeadToHead:
    """
    Scenario: Compare two teams head-to-head
      Given the match data is loaded
      When I compare "Flamengo" and "Fluminense" in the Brasileirão
      Then I receive wins for each side, draws and the meetings
    """

    def test_when_comparing_fla_flu_in_the_brasileirao_then_the_record_is_consistent(self, engine):
        h2h = engine.head_to_head("Flamengo", "Fluminense", competition="Brasileirão")
        assert isinstance(h2h, HeadToHead)
        assert h2h.total == 42
        assert (h2h.team_a_wins, h2h.draws, h2h.team_b_wins) == (17, 11, 14)
        assert h2h.team_a_wins + h2h.draws + h2h.team_b_wins == h2h.total

    def test_when_comparing_teams_then_all_matches_involve_both_teams(self, engine):
        h2h = engine.head_to_head("Palmeiras", "Santos")
        assert h2h.total > 30
        for match in h2h.matches:
            assert {match.home_key, match.away_key} == {"palmeiras", "santos-sp"}

    def test_when_comparing_a_team_with_itself_then_an_error_is_raised(self, engine):
        from brazilian_soccer_mcp.queries import QueryError

        try:
            engine.head_to_head("Flamengo", "Fla")
        except QueryError:
            pass
        else:
            raise AssertionError("expected QueryError when comparing a team with itself")


class TestFindTeam:
    """
    Scenario: Resolve a team and report its activity
      Given the match data is loaded
      When I look up "Timão"
      Then I learn it is Corinthians, with matches, competitions and variants
    """

    def test_when_looking_up_a_nickname_then_the_team_profile_is_returned(self, engine):
        info = engine.find_team("Timão")
        assert info.key == "corinthians"
        assert info.match_count > 1000
        assert "Brasileirão Série A" in info.competitions
        assert "Copa Libertadores" in info.competitions
        assert info.first_match < info.last_match

    def test_when_looking_up_an_ambiguous_base_name_then_siblings_are_reported(self, engine):
        info = engine.find_team("Botafogo")
        assert info.key == "botafogo-rj"
        siblings = " ".join(info.siblings)
        assert "Botafogo" in siblings


class TestListTeams:
    """
    Scenario: List teams in a competition season
      Given the match data is loaded
      When I list the 2019 Brasileirão Série A teams
      Then all twenty clubs appear with match counts
    """

    def test_when_listing_serie_a_2019_teams_then_twenty_clubs_appear(self, engine):
        teams = engine.list_teams(competition="Série A", season=2019)
        assert len(teams) == 20
        names = [name for name, _ in teams]
        assert "Flamengo" in names
        counts = [count for _, count in teams]
        assert all(count == 38 for count in counts)
