"""Feature: Statistical Analysis (BDD)

Spec scenarios:

    Scenario: Average goals per match
      Given the match data is loaded
      When I ask for average goals in the Brasileirão
      Then I receive the average plus home/draw/away win rates

    Scenario: Biggest wins in the dataset
      When I ask for the biggest victories
      Then they are ranked by goal margin

    Scenario: Best home/away records
      When I ask which team has the best away record
      Then teams are ranked by win rate
"""

from __future__ import annotations

import pytest

from brsoccer import queries as q

pytestmark = pytest.mark.bdd


class TestAverageGoalsPerMatch:
    """Scenario: What's the average goals per match in the Brasileirão?"""

    def test_serie_a_average_goals(self, sd):
        # When I ask for aggregate stats over the whole Brasileirão
        stats = q.competition_stats(sd, "serie_a")
        # Then 8,403 scored matches average ~2.57 goals
        assert stats["matches"] == 8403
        assert stats["avg_goals"] == pytest.approx(2.57, abs=0.05)
        # And home teams win about half the time
        assert 45.0 <= stats["home_win_rate"] <= 55.0
        # And the three rates add up to 100%
        total = stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"]
        assert total == pytest.approx(100.0, abs=0.01)

    def test_season_comparison_2018_vs_2019(self, sd):
        # When I compare the 2018 and 2019 seasons
        s2018 = q.competition_stats(sd, "serie_a", 2018)
        s2019 = q.competition_stats(sd, "serie_a", 2019)
        # Then both seasons are complete (380 matches)
        assert s2018["matches"] == 380 and s2019["matches"] == 380
        # And 2019 was higher-scoring (2.31 vs 2.18 goals per match)
        assert s2019["avg_goals"] == pytest.approx(2.31, abs=0.01)
        assert s2018["avg_goals"] == pytest.approx(2.18, abs=0.01)
        assert s2019["avg_goals"] > s2018["avg_goals"]

    def test_dataset_wide_stats(self, sd):
        # When I ask for stats with no competition filter
        stats = q.competition_stats(sd)
        # Then every scored match in the dataset is included
        assert stats["matches"] > 15000


class TestBiggestWins:
    """Scenario: Show me the biggest wins in the dataset."""

    def test_biggest_wins_overall(self, sd):
        # When I ask for the biggest victories dataset-wide
        wins = q.biggest_wins(sd, limit=5)
        # Then they are ranked by descending goal margin
        margins = [w.margin for w in wins]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] == 8
        # And River Plate 8-0 Jorge Wilstermann (2017 Libertadores) tops it
        assert wins[0].date.isoformat() == "2017-09-21"
        assert wins[0].home_display == "River Plate"
        assert (wins[0].home_goal, wins[0].away_goal) == (8, 0)

    def test_biggest_win_includes_a_brazilian_copa_thrashing(self, sd):
        # When I ask for the biggest Copa do Brasil wins
        wins = q.biggest_wins(sd, competition="copa_do_brasil", limit=3)
        # Then São Paulo 9-1 4 de Julho (2021) is among them
        top3 = [w for w in wins if w.margin >= 8]
        sao_paulo = next(w for w in top3 if w.home_display == "São Paulo")
        assert (sao_paulo.home_goal, sao_paulo.away_goal) == (9, 1)
        assert sao_paulo.season == 2021

    def test_biggest_wins_for_one_team(self, sd):
        # When I ask for Flamengo's biggest wins
        wins = q.biggest_wins(sd, team="Flamengo", limit=5)
        # Then every match involves Flamengo and margins are sorted
        flamengo = q.resolve_team(sd, "Flamengo")
        assert wins and all(w.involves(flamengo) for w in wins)
        margins = [w.margin for w in wins]
        assert margins == sorted(margins, reverse=True)


class TestBestRecords:
    """Scenario: Which team has the best home/away record?"""

    def test_best_home_record(self, sd):
        # When I rank teams by home win rate (100+ matches)
        ranked = q.best_records(sd, venue="home", min_matches=100, limit=3)
        # Then Palmeiras leads the all-time home table
        assert ranked[0]["display"] == "Palmeiras"
        assert ranked[0]["win_rate"] == pytest.approx(60.2, abs=0.5)
        assert ranked[0]["matches"] > 400

    def test_best_away_record(self, sd):
        # When I rank teams by away win rate
        ranked = q.best_records(sd, venue="away", min_matches=100, limit=3)
        # Then a traditional big club leads away too
        assert ranked[0]["display"] == "Palmeiras"
        assert ranked[0]["win_rate"] == pytest.approx(34.8, abs=0.5)

    def test_invalid_venue_is_rejected(self, sd):
        # When I pass an invalid venue
        with pytest.raises(q.QueryError, match="venue"):
            q.best_records(sd, venue="neutral")

    def test_min_matches_filters_small_samples(self, sd):
        # When I require 300+ matches
        ranked = q.best_records(sd, venue="home", min_matches=300, limit=50)
        # Then only teams with at least 300 home matches appear
        assert ranked
        assert all(r["matches"] >= 300 for r in ranked)


class TestHomeVsAwayPerformance:
    """Scenario: Home vs away performance asymmetry."""

    def test_home_advantage_exists(self, sd):
        # When I compute dataset-wide win rates
        stats = q.competition_stats(sd)
        # Then home teams win clearly more often than away teams
        assert stats["home_win_rate"] > stats["away_win_rate"] + 15.0


class TestDerbies:
    """Scenario: Show me all derbies in 2023."""

    def test_derbies_2019(self, sd):
        # When I ask for 2019 derbies
        groups = q.derbies(sd, season=2019)
        names = {name for name, _ in groups}
        # Then the six big-state clashes are present (Coritiba was in
        # Serie B and Bahia/Vitoria in different divisions: no Atletiba,
        # no Ba-Vi that year)
        assert {"Fla-Flu", "GreNal", "Clássico Majestoso", "Choque-Rei", "San-São", "Clássico dos Milhões"} <= names
        assert "Ba-Vi" not in names
        assert "Atletiba" not in names
        # And Fla-Flu happened twice that season
        fla_flu = next(matches for name, matches in groups if name == "Fla-Flu")
        assert len(fla_flu) == 2

    def test_derbies_2023(self, sd):
        # When I ask for 2023 derbies
        groups = q.derbies(sd, season=2023)
        names = {name for name, _ in groups}
        # Then seven rivalries met in 2023 (Bahia and Vitória were in
        # different divisions, so no Ba-Vi)
        assert names == {
            "Fla-Flu",
            "Clássico dos Milhões",
            "Clássico Majestoso",
            "Choque-Rei",
            "San-São",
            "GreNal",
            "Atletiba",
        }
        choque_rei = next(m for n, m in groups if n == "Choque-Rei")
        assert len(choque_rei) == 4  # league (2) + Copa do Brasil semi legs (2)

    def test_derbies_dataset_wide_include_ba_vi(self, sd):
        # When I ask for derbies across the whole dataset
        groups = q.derbies(sd)
        # Then the Ba-Vi (Bahia vs Vitória) derby appears
        names = {name for name, _ in groups}
        assert "Ba-Vi" in names
        ba_vi = next(m for n, m in groups if n == "Ba-Vi")
        assert len(ba_vi) >= 10
