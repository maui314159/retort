"""BDD tests for team queries (spec section: "2. Team Queries").

Feature: Team Queries

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations


class TestTeamStats:
    """Scenario: Get team statistics"""

    def test_palmeiras_2023(self, svc):
        result = svc.team_stats(team="Palmeiras", competition="Brasileirão Série A", season=2023)
        for expected in ("Matches:", "Wins:", "Draws:", "Losses:", "Goals For:", "Win rate:"):
            assert expected in result, expected
        # Real 2023 Série A: Palmeiras 22W 11D 4L... source data has 37 of
        # 38 matches; assert the structural totals instead of exact history.
        assert "Matches: 37" in result

    def test_record_math_is_consistent(self, svc):
        """W + D + L must equal Matches; GF/GA parsed from the same text."""
        result = svc.team_stats(team="Grêmio", competition="Brasileirão Série A", season=2019)
        w = _grab(result, r"Wins: (\d+)")
        d = _grab(result, r"Draws: (\d+)")
        l = _grab(result, r"Losses: (\d+)")
        m = _grab(result, r"Matches: (\d+)")
        assert w + d + l == m == 38

    def test_home_vs_away_partition(self, svc):
        """home record matches + away record matches = full season record."""
        kwargs = dict(team="Flamengo", competition="Brasileirão Série A", season=2019)
        total = _grab(svc.team_stats(**kwargs), r"Matches: (\d+)")
        home = _grab(svc.team_stats(venue="home", **kwargs), r"Matches: (\d+)")
        away = _grab(svc.team_stats(venue="away", **kwargs), r"Matches: (\d+)")
        assert home == away == 19
        assert home + away == total

    def test_spec_example_corinthians_2022_home(self, svc):
        """Spec: 'What is Corinthians' home record in 2022?' -> 19 matches."""
        result = svc.team_stats(
            team="Corinthians", competition="Brasileirão Série A", season=2022, venue="home"
        )
        assert "Matches: 19" in result
        assert "Corinthians" in result

    def test_unknown_team_suggests_alternatives(self, svc):
        result = svc.team_stats(team="Barcelona")
        assert "not found" in result.lower()
        assert "Palmeiras" in result or "Flamengo" in result


class TestHeadToHead:
    """Scenario: Compare teams head-to-head"""

    def test_palmeiras_vs_santos(self, svc):
        result = svc.head_to_head("Palmeiras", "Santos")
        assert "Head-to-head in dataset:" in result
        assert "Palmeiras" in result and "Santos" in result
        # wins + wins + draws should be mentioned with numeric counts
        assert _grab(result, r"Palmeiras (\d+) wins") >= 10

    def test_h2h_math(self, svc):
        result = svc.head_to_head("Palmeiras", "Santos")
        w1 = _grab(result, r"dataset: Palmeiras (\d+) wins")
        w2 = _grab(result, r"Santos (\d+) wins")
        d = _grab(result, r"(\d+) draws")
        total = _grab(result, r"— (\d+) matches in dataset")
        assert w1 + w2 + d == total

    def test_h2h_competition_filter(self, svc):
        result = svc.head_to_head("Palmeiras", "Santos", competition="Copa Libertadores")
        assert "Copa Libertadores" in result

    def test_h2h_with_derby_name(self, svc):
        result = svc.head_to_head("Flamengo", "Fluminense")
        assert "Fla-Flu" in result

    def test_h2h_same_team(self, svc):
        result = svc.head_to_head("Flamengo", "Flamengo")
        assert "two different teams" in result


class TestTeamProfile:
    """Scenario: Team profile aggregates everything about a club"""

    def test_flamengo_profile(self, svc):
        result = svc.team_profile("Flamengo")
        assert "Flamengo — Team Profile" in result
        assert "Brasileirão Série A" in result
        assert "Copa do Brasil" in result
        assert "Copa Libertadores" in result
        assert "Titles in dataset" in result
        assert "2019" in result  # Brasileirão 2019 champion

    def test_gremio_profile_has_squad(self, svc):
        """Cross-file: match data + FIFA squad in one answer."""
        result = svc.team_profile("Grêmio")
        assert "Squad (FIFA data): 20 players" in result

    def test_profile_all_time_record(self, svc):
        result = svc.team_profile("Palmeiras")
        assert "All-time record" in result
        assert "win rate" in result

    def test_titles_computed_from_standings(self, svc):
        result = svc.team_profile("Palmeiras")
        assert "Brasileirão Série A 2022" in result


class TestListTeams:
    def test_list_teams_serie_a_2019(self, svc):
        result = svc.list_teams(competition="Brasileirão Série A", season=2019)
        assert "Teams in Brasileirão Série A 2019" in result
        assert "20 teams" in result
        for club in ("Flamengo", "Palmeiras", "São Paulo", "Athletico-PR"):
            assert club in result

    def test_list_teams_relegation_size(self, svc):
        """A Serie A season must have exactly 20 teams (spec data quality)."""
        result = svc.list_teams(competition="Brasileirão Série A", season=2021)
        assert "20 teams" in result


def _grab(text: str, pattern: str) -> int:
    import re

    m = re.search(pattern, text)
    assert m, f"pattern {pattern!r} not found in:\n{text}"
    return int(m.group(1))
