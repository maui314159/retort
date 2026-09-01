"""
BDD scenarios: team queries (TASK.md "Required Capabilities" #2).

Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.models import BRASILEIRAO_A


class TestTeamRecord:
    """Scenario: get team statistics (spec Gherkin example)."""

    def test_palmeiras_2023_stats(self, service):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        stats = service.team_record("Palmeiras", season=2023)
        # Then I should receive wins, losses, draws, and goals
        r = stats.record
        assert r.matches == r.wins + r.draws + r.losses
        assert r.goals_for > 0 and r.goals_against > 0
        # 2023: 37 league matches (BRFB) + 6 cup matches
        assert r.matches == 43

    def test_venue_split_is_consistent(self, service):
        # Given a season record with home/away split
        stats = service.team_record("Palmeiras", season=2023)
        total = stats.record
        home, away = stats.home_record, stats.away_record
        # Then home + away reconcile with the overall record
        assert total.matches == home.matches + away.matches
        assert total.wins == home.wins + away.wins
        assert total.draws == home.draws + away.draws
        assert total.losses == home.losses + away.losses
        assert total.goals_for == home.goals_for + away.goals_for
        assert total.goals_against == home.goals_against + away.goals_against

    def test_home_only_record(self, service):
        # Given 'What is Corinthians' home record in 2022?'
        # When I request the home-only record for the league
        stats = service.team_record(
            "Corinthians", season=2022, competition="brasileirao", venue="home"
        )
        r = stats.record
        # Then only home league matches are counted
        # (the dataset leaves the last 2022 rounds unplayed: 15 of 19)
        assert r.matches == 15
        assert (r.wins, r.draws, r.losses) == (10, 4, 1)
        assert (r.goals_for, r.goals_against) == (21, 7)

    def test_competition_filter(self, service):
        all_comps = service.team_record("Flamengo", season=2019)
        league_only = service.team_record("Flamengo", season=2019, competition="brasileirao")
        # Flamengo also played Copa do Brasil + Libertadores in 2019
        assert all_comps.record.matches > league_only.record.matches
        assert league_only.record.matches == 38

    def test_invalid_venue_rejected(self, service):
        with pytest.raises(ValueError):
            service.team_record("Flamengo", venue="neutral")


class TestHeadToHead:
    """Scenario: 'Compare Palmeiras and Santos head-to-head'."""

    def test_palmeiras_vs_santos(self, service):
        h2h = service.head_to_head("Palmeiras", "Santos")
        total = h2h.a_wins + h2h.b_wins + h2h.draws
        # Then every played match is classified exactly once
        played = sum(1 for m in h2h.matches if m.played())
        assert total == played > 0
        # And goal totals are consistent with the match list
        listed = sum(
            (m.home_goals if m.home_id == "palmeiras" else m.away_goals)
            for m in h2h.matches
            if m.played()
        )
        assert listed == h2h.a_goals

    def test_fla_flu_record(self, service):
        h2h = service.head_to_head("Flamengo", "Fluminense")
        assert (h2h.a_wins, h2h.b_wins, h2h.draws) == (18, 15, 13)

    def test_h2h_respects_competition_filter(self, service):
        league = service.head_to_head("Flamengo", "Fluminense", competition="brasileirao")
        cup = service.head_to_head("Flamengo", "Fluminense", competition="Copa do Brasil")
        assert all(m.competition == BRASILEIRAO_A for m in league.matches)
        assert all(m.competition == "Copa do Brasil" for m in cup.matches)

    def test_symmetry(self, service):
        forward = service.head_to_head("Flamengo", "Fluminense")
        backward = service.head_to_head("Fluminense", "Flamengo")
        assert forward.a_wins == backward.b_wins
        assert forward.draws == backward.draws


class TestTeamOverview:
    """Scenario: 'What competitions has Palmeiras played in?'."""

    def test_palmeiras_overview(self, service):
        info = service.team_overview("Palmeiras")
        # Then competitions + seasons are reported across all files
        assert set(info["competitions"]) >= {
            "Brasileirão Série A",
            "Copa do Brasil",
            "Copa Libertadores",
        }
        serie_a_seasons = info["competitions"]["Brasileirão Série A"]
        assert serie_a_seasons[0] == 2004   # Palmeiras was in Série B in 2003
        assert serie_a_seasons[-1] == 2023
        # And the all-time record reconciles with W+D+L
        record = info["record"]
        assert record.matches == record.wins + record.draws + record.losses
        assert record.matches == 899

    def test_cross_file_squad_bridge(self, service):
        # Given a club present in both match data and the FIFA snapshot
        info = service.team_overview("Santos")
        # Then the overview reports its FIFA squad size
        assert info["squad_in_fifa"] is True
        assert info["squad_size"] == 20
        # And a club missing from FIFA says so
        flamengo = service.team_overview("Flamengo")
        assert flamengo["squad_in_fifa"] is False

    def test_name_variants_reported(self, service):
        info = service.team_overview("Atlético Mineiro")
        # The registry saw both 'Atlético-MG' and 'Atletico-MG' spellings
        assert len(info["variants"]) >= 1


class TestFormatting:
    """Scenario: team records render like TASK.md's example answer format."""

    def test_record_block_format(self, service):
        from brazilian_soccer_mcp.formatting import format_team_stats

        stats = service.team_record(
            "Corinthians", season=2022, competition="brasileirao", venue="home"
        )
        text = format_team_stats(stats)
        # Mirrors: 'Corinthians home record (2022 Brasileirão):' block
        assert text.startswith("Corinthians home record (2022")
        assert "- Matches: 15" in text
        assert "- Wins: 10, Draws: 4, Losses: 1" in text
        assert "- Goals For: 21, Goals Against: 7" in text
        assert "- Win rate: 66.7%" in text

    def test_h2h_summary_line(self, service):
        from brazilian_soccer_mcp.formatting import format_head_to_head

        text = format_head_to_head(service.head_to_head("Flamengo", "Fluminense"))
        assert "Head-to-head in dataset: Flamengo 18 wins, Fluminense 15 wins, 13 draws" in text
        assert "(Fla-Flu)" in text  # derby name detected
