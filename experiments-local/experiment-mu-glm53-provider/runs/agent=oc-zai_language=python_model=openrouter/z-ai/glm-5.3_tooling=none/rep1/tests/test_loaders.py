"""
BDD scenarios: dataset loading.

Feature: All six CSV files are loadable and queryable
  TASK.md "Success Criteria" -> "Data Coverage": every provided dataset
  must load; the multi-format dates must parse; UTF-8 names must survive;
  and fixtures that two sources both record must not double-count.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer_mcp.loaders import (
    parse_date,
    parse_height_cm,
    parse_weight_kg,
    to_int,
)
from brazilian_soccer_mcp.models import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
)


class TestTolerantParsers:
    """Scenario Outline: every date/score format found in the data."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2012-05-19 18:30:00", date(2012, 5, 19)),  # ISO + time
            ("2023-09-24", date(2023, 9, 24)),           # ISO date
            ("29/03/2003", date(2003, 3, 29)),           # Brazilian DD/MM/YYYY
            ("NA", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parse_date_formats(self, raw, expected):
        assert parse_date(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2", 2),
            ('"2"', 2),       # quoted score from Libertadores file
            ("2.0", 2),       # float score from BR-Football file
            ("NA", None),
            ("", None),
            ("junk", None),
        ],
    )
    def test_to_int_tolerant(self, raw, expected):
        assert to_int(raw) == expected

    def test_fifa_unit_conversions(self):
        # Given FIFA imperial units
        # When I convert them
        # Then metric values come back (5'9" = 175 cm, 150 lbs = 68 kg)
        assert parse_height_cm("5'9") == 175
        assert parse_weight_kg("150lbs") == 68


class TestDataCoverage:
    """Scenario: all six CSV files are loadable."""

    def test_all_six_sources_were_read(self, data):
        # Given the loader ran over data/kaggle
        # Then all six files contributed rows
        expected_files = {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
            "fifa_data.csv",
        }
        assert expected_files <= set(data.source_row_counts)
        # And row counts match the TASK.md "Provided Data" table
        assert data.source_row_counts["Brasileirao_Matches.csv"] == 4180
        assert data.source_row_counts["Brazilian_Cup_Matches.csv"] == 1337
        assert data.source_row_counts["Libertadores_Matches.csv"] == 1255
        assert data.source_row_counts["BR-Football-Dataset.csv"] == 10296
        assert data.source_row_counts["novo_campeonato_brasileiro.csv"] == 6886
        assert data.source_row_counts["fifa_data.csv"] == 18207

    def test_matches_and_players_loaded(self, data):
        assert 15_000 < len(data.matches) < 20_000
        assert len(data.players) == 18207  # TASK.md: 18,207 players

    def test_all_five_competitions_present(self, data):
        competitions = {m.competition for m in data.matches}
        assert competitions == {
            BRASILEIRAO_A,
            BRASILEIRAO_B,
            BRASILEIRAO_C,
            COPA_DO_BRASIL,
            LIBERTADORES,
        }

    def test_utf8_names_survive(self, data):
        # Given accented club names exist in the sources
        # When I look for their display names
        # Then the accents survive round-tripping
        displays = {m.home_display for m in data.matches}
        assert any("São Paulo" in d for d in displays)
        assert any("Grêmio" in d for d in displays)

    def test_team_index_covers_every_match(self, data):
        # Given the team -> matches index
        # Then every match is reachable from both participants
        indexed = data.matches_by_team
        for match in data.matches:
            assert match in indexed.get(match.home_id, [])
            assert match in indexed.get(match.away_id, [])

    def test_broken_rows_are_skipped_not_crashing(self, data):
        # Given Libertadores contains an all-'NA' row (Flamengo x Athletico)
        # When loading finishes
        # Then exactly that one row was skipped and no crash happened
        assert data.skipped_rows == 1


class TestDeduplication:
    """Scenario: overlapping sources must not double-count fixtures."""

    def test_duplicates_removed(self, data):
        # Série A 2012-2019 is in two files; Copa do Brasil 2014-2021 too
        # Given ~24k raw match rows minus the skipped one
        raw = sum(data.source_row_counts[f] for f in data.source_row_counts if f != "fifa_data.csv")
        # When deduplication runs
        # Then thousands of cross-source duplicates are removed
        assert data.duplicates_removed > 5000
        assert len(data.matches) == raw - data.skipped_rows - data.duplicates_removed

    def test_2019_serie_a_not_duplicated(self, service):
        # Given the 2019 Série A season appears in three source files
        # When I aggregate from the single authoritative source
        matches = service.primary_matches(BRASILEIRAO_A, 2019)
        # Then each of the 20 teams played exactly 38 matches (380 total)
        assert len(matches) == 380

    def test_primary_source_prefers_authority(self, service):
        # Given Série A 2021 exists in Brasileirao_Matches (380) and
        # BR-Football (491 rows, inflated by calendar-year mislabelling)
        # When choosing the primary source
        # Then the dedicated Brasileirão file wins
        assert service.primary_source(BRASILEIRAO_A, 2021) == "Brasileirao_Matches.csv"
        # And 2023 (only in BR-Football) falls back to it
        assert service.primary_source(BRASILEIRAO_A, 2023) == "BR-Football-Dataset.csv"
        # And 2003-2011 falls back to the historical file
        assert service.primary_source(BRASILEIRAO_A, 2005) == "novo_campeonato_brasileiro.csv"
