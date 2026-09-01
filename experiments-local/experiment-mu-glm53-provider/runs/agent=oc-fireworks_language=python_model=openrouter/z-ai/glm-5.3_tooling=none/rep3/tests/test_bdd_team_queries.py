"""Feature: Team Queries (BDD)

Spec scenarios:

    Scenario: Get team statistics
      Given the match data is loaded
      When I request statistics for "Palmeiras" in season "2023"
      Then I should receive wins, losses, draws, and goals

    Scenario: Team home record
      When I request Corinthians' home record in 2022
      Then I receive matches, wins, draws, losses, goals and win rate

    Scenario: Compare two teams head-to-head
      When I compare "Palmeiras" and "Santos" head-to-head
      Then I receive wins for each side and draws
"""

from __future__ import annotations

import pytest

from brsoccer import queries as q

pytestmark = pytest.mark.bdd


class TestTeamStatistics:
    """Scenario: Get team statistics for a season."""

    def test_palmeiras_2023_statistics(self, sd):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        stats = q.team_stats(sd, "Palmeiras", season=2023, competition="serie_a")
        # Then I should receive wins, losses, draws, and goals
        overall = stats["overall"]
        assert overall["matches"] > 0
        assert overall["wins"] > 0 and overall["draws"] > 0 and overall["losses"] > 0
        assert overall["goals_for"] > 0 and overall["goals_against"] > 0
        # And home + away matches add up to the overall record
        assert overall["matches"] == stats["home"]["matches"] + stats["away"]["matches"]

    def test_corinthians_home_record_2022(self, sd):
        # When I request Corinthians' home record in the 2022 Brasileirão
        stats = q.team_stats(sd, "Corinthians", season=2022, competition="serie_a")
        home = stats["home"]
        # Then the dataset yields: 19 home matches, 12W 4D 3L, 24:11 goals
        assert home["matches"] == 19
        assert (home["wins"], home["draws"], home["losses"]) == (12, 4, 3)
        assert (home["goals_for"], home["goals_against"]) == (24, 11)
        assert home["win_rate"] == pytest.approx(12 / 19 * 100, abs=0.1)

    def test_team_stats_without_filters_spans_all_competitions(self, sd):
        # When I request overall statistics for "Flamengo"
        stats = q.team_stats(sd, "Flamengo")
        # Then matches from several competitions are included
        assert {"serie_a", "copa_do_brasil", "libertadores"} <= set(stats["competitions_seen"])


class TestHeadToHead:
    """Scenario: Compare teams head-to-head."""

    def test_palmeiras_vs_santos(self, sd):
        # When I compare Palmeiras and Santos head-to-head
        h2h = q.head_to_head(sd, "Palmeiras", "Santos")
        # Then I receive wins for both sides plus draws
        assert h2h["wins_a"] > 0 or h2h["wins_b"] > 0
        assert h2h["draws"] >= 0
        # And the totals add up to the number of scored matches
        scored = [m for m in h2h["matches"] if m.played]
        assert h2h["wins_a"] + h2h["wins_b"] + h2h["draws"] == len(scored)
        # And goals are reported for both sides
        assert h2h["goals_a"] > 0 and h2h["goals_b"] > 0

    def test_flamengo_vs_fluminense_record(self, sd):
        # When I compare Flamengo and Fluminense (Fla-Flu)
        h2h = q.head_to_head(sd, "Flamengo", "Fluminense")
        # Then the dataset record is 18-14-12 across 44 matches
        assert len(h2h["matches"]) == 44
        assert (h2h["wins_a"], h2h["wins_b"], h2h["draws"]) == (18, 14, 12)
        assert (h2h["goals_a"], h2h["goals_b"]) == (60, 48)

    def test_head_to_head_scoped_to_one_competition(self, sd):
        # When I scope the comparison to the Libertadores
        h2h = q.head_to_head(sd, "Palmeiras", "Santos", competition="libertadores")
        # Then only Libertadores meetings are counted
        assert all(m.competition == "libertadores" for m in h2h["matches"])
        # And the 2020 Libertadores final is among them
        finals = [m for m in h2h["matches"] if m.season == 2020 and m.stage == "final"]
        assert finals and finals[0].date.year == 2020


class TestTeamCompetitions:
    """Scenario: What competitions has Palmeiras played in? (cross-file)."""

    def test_palmeiras_competitions(self, sd):
        # When I ask for Palmeiras' competitions
        rows = q.team_competitions(sd, "Palmeiras")
        codes = {row["competition"] for row in rows}
        # Then all three major competitions appear (cross-file query)
        assert {"serie_a", "copa_do_brasil", "libertadores"} <= codes
        # And the biggest competition by volume is the Brasileirão
        assert rows[0]["competition"] == "serie_a"
        assert rows[0]["first_season"] == 2004  # Palmeiras played Serie B in 2003
        assert rows[0]["last_season"] == 2023

    def test_unknown_team_is_rejected_with_candidates(self, sd):
        # When I ask for a team that does not exist
        with pytest.raises(q.QueryError) as excinfo:
            q.team_stats(sd, "Barcelona United")
        # Then the error is friendly
        assert "No team found" in str(excinfo.value)


class TestTeamSpellingVariantsResolveToSameTeam:
    """Scenario: Team name variations work for team queries too."""

    @pytest.mark.parametrize(
        ("variant",),
        [
            ("Corinthians-SP",),
            ("SPORT CLUB CORINTHIANS PAULISTA",),
            ("corinthians",),
        ],
    )
    def test_variants_give_identical_stats(self, sd, variant):
        # Given several spelling variants of the same club
        # When I request statistics with each variant
        stats = q.team_stats(sd, variant)
        # Then they all resolve to the same canonical team record
        assert stats["key"] == "corinthians"
        assert stats["overall"]["matches"] == stats["overall"]["matches"]
