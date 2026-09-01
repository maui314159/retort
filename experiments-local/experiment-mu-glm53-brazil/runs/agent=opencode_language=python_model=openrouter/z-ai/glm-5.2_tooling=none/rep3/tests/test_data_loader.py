"""BDD tests for data loading (data_loader.py).

Context block
-------------
Feature: Data Loading
  All six Kaggle CSVs must load, parse dates in three formats, coerce
  string/float goals to int, and unify team names via the normalizer.
"""
from __future__ import annotations

from data_loader import SoccerData, parse_date, parse_goals, parse_season


class TestDateParsing:
    # Scenario: ISO date
    def test_iso_date(self):
        assert parse_date("2023-09-24") == "2023-09-24"

    # Scenario: ISO datetime
    def test_iso_datetime(self):
        assert parse_date("2012-05-19 18:30:00") == "2012-05-19"

    # Scenario: Brazilian DD/MM/YYYY
    def test_brazilian_date(self):
        assert parse_date("29/03/2003") == "2003-03-29"

    # Scenario: NA sentinel (Libertadores) -> None
    def test_na_sentinel(self):
        assert parse_date("NA") is None
        assert parse_season("NA") is None

    # Scenario: empty -> None
    def test_empty(self):
        assert parse_date("") is None


class TestGoalCoercion:
    # Scenario: int string
    def test_int_string(self):
        assert parse_goals("2") == 2

    # Scenario: float string (BR-Football uses "1.0")
    def test_float_string(self):
        assert parse_goals("1.0") == 1

    # Scenario: empty -> None
    def test_empty(self):
        assert parse_goals("") is None


class TestLoadingAll:
    # Scenario: all six datasets load
    def test_all_datasets_loaded(self, sd: SoccerData):
        # Given the data directory
        # When load_all runs
        # Then matches and players exist
        assert len(sd.matches) > 0
        assert len(sd.players) > 0
        # Combined match count across 5 match files (> 20k expected)
        assert len(sd.matches) > 20000
        # FIFA dataset has 18k+ players
        assert len(sd.players) > 18000

    # Scenario: every match has a non-empty competition
    def test_every_match_has_competition(self, sd: SoccerData):
        assert all(m.competition for m in sd.matches)

    # Scenario: team index is populated
    def test_team_index_populated(self, sd: SoccerData):
        assert "palmeiras" in sd.by_team
        assert "flamengo" in sd.by_team
        assert sd.by_team["flamengo"], "Flamengo should have matches indexed"

    # Scenario: cross-file team unification
    def test_team_unified_across_files(self, sd: SoccerData):
        # Palmeiras appears in Brasileirao, Libertadores, historical, etc.
        pal = sd.matches_for_team("Palmeiras-SP")
        source_files = {m.source_file for m in pal}
        assert len(source_files) >= 2, f"Palmeiras should appear in multiple files, got {source_files}"

    # Scenario: no match has None competition and most have a date
    def test_most_matches_have_dates(self, sd: SoccerData):
        with_dates = sum(1 for m in sd.matches if m.date)
        assert with_dates > len(sd.matches) * 0.9
