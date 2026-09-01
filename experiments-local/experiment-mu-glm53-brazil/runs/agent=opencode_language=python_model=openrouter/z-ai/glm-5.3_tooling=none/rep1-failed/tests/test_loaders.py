"""BDD tests for dataset loading and cross-file deduplication.

Feature: Data loading
  All six CSV files must be loaded, parsed and unified so that the same
  fixture present in several files counts exactly once while genuinely
  different matches (e.g. Libertadores group stage vs round of 16 between
  the same teams) are preserved.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from soccer_mcp.loaders import COMPETITIONS, parse_date, parse_int


class TestParsers:
    """Scenario: Tolerant value parsing
    Given the datasets' mixed date/goal encodings
    Then every observed format parses to a date or None
    """

    def test_parse_date_formats(self):
        assert parse_date("2023-09-24") == (date(2023, 9, 24), None)
        assert parse_date("2012-05-19 18:30:00") == (date(2012, 5, 19), "18:30")
        assert parse_date("29/03/2003") == (date(2003, 3, 29), None)
        assert parse_date("NA") == (None, None)
        assert parse_date("") == (None, None)

    def test_parse_int_formats(self):
        assert parse_int("2") == 2
        assert parse_int("2.0") == 2
        assert parse_int("0.0") == 0
        assert parse_int("NA") is None
        assert parse_int("-") is None
        assert parse_int("") is None


class TestLoadAllFiles:
    """Scenario: Load all six CSV files
    Given the data directory
    Then all six datasets are loaded with plausible row counts
    """

    def test_all_files_loaded(self, kb):
        assert len(kb.players) == 18_207, "FIFA dataset row count"
        assert len(kb.matches) > 15_000
        assert len(kb.registry.teams) > 300

    def test_competitions_present(self, kb):
        comps = {m.competition for m in kb.matches}
        assert {
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        } <= comps

    def test_player_fields(self, players):
        neymar = [p for p in players if p.name == "Neymar Jr"]
        assert neymar, "Neymar Jr must be in the FIFA dataset"
        p = neymar[0]
        assert p.nationality == "Brazil"
        assert p.club == "Paris Saint-Germain"
        assert p.overall is not None and p.overall >= 90
        assert p.position_group == "FWD"

    def test_match_fields(self, matches):
        """Every match has competition, teams and either a score or None."""
        for m in matches:
            assert m.competition
            assert m.home and m.away
            assert (m.home_goals is None) == (m.away_goals is None)


class TestDeduplication:
    """Scenario: The same fixture in multiple files counts once
    Given the 2012-2019 Brasileirão present in two files and the
    2014-2022 seasons present in three files
    Then each season has exactly one match per ordered team pair
    """

    def test_serie_a_season_sizes(self, kb):
        """League season sizes reconcile with known source gaps.

        2003/2004 had 46 rounds (552 matches), 2005 had 42 (462),
        2006-2023 have 38 rounds (380). Known gaps: 2009 is missing one
        fixture in the source, 2023 is missing three.
        """
        by_season = Counter(
            m.season for m in kb.matches if m.competition == "Brasileirão Série A"
        )
        assert by_season[2003] == 552
        assert by_season[2004] == 552
        assert by_season[2005] == 462
        for year in range(2006, 2009):
            assert by_season[year] == 380, year
        for year in range(2010, 2023):
            assert by_season[year] == 380, year
        assert by_season[2009] == 379  # one fixture missing in the source
        assert by_season[2023] == 377  # three fixtures missing in the source

    def test_no_duplicate_ordered_pairs_in_leagues(self, kb):
        for comp in ("Brasileirão Série A", "Brasileirão Série B", "Brasileirão Série C"):
            pairs = Counter(
                (m.season, m.home, m.away)
                for m in kb.matches
                if m.competition == comp
            )
            dups = {k: v for k, v in pairs.items() if v > 1}
            assert not dups, f"{comp} has duplicate fixtures: {list(dups)[:5]}"

    def test_libertadores_group_vs_knockout_preserved(self, kb):
        """Atlético-MG and São Paulo met in the 2013 group stage AND round
        of 16 with the same venue orders - all four matches must survive."""
        ms = [
            m
            for m in kb.matches
            if m.competition == "Copa Libertadores"
            and m.season == 2013
            and {m.home, m.away} == {"atletico|MG", "sao paulo|SP"}
        ]
        assert len(ms) == 4
        labels = sorted(m.round_label for m in ms)
        assert labels == ["Group Stage", "Group Stage", "Round of 16", "Round of 16"]

    def test_libertadores_match_count(self, kb):
        """All 1,255 Libertadores rows are distinct matches."""
        n = sum(1 for m in kb.matches if m.competition == "Copa Libertadores")
        assert n == 1_255

    def test_self_matches_dropped(self, kb):
        assert not any(m.home == m.away for m in kb.matches)

    def test_2022_missing_scores_repaired(self, kb):
        """Brasileirao_Matches.csv lacks 81 scores for 2022; BR-Football
        data covers every one of them, so after the merge the 2022 season
        is fully scored."""
        ms = [m for m in kb.matches if m.competition == "Brasileirão Série A" and m.season == 2022]
        assert len(ms) == 380
        assert all(m.has_score for m in ms), "2022 scores should be repaired from BR-Football"


class TestCrossFileMerge:
    """Scenario: Fields missing in one file are filled from another
    Given a Serie A match recorded without a score in one file
    Then the score is filled from the duplicate row in another file
    """

    def test_score_repair_example(self, kb):
        ms = [
            m
            for m in kb.matches
            if m.competition == "Brasileirão Série A"
            and m.season == 2022
            and m.home == "corinthians|SP"
            and m.away == "atletico|PR"
        ]
        assert len(ms) == 1
        assert ms[0].has_score, "2022 Corinthians vs Athletico-PR score should be repaired from BR-Football"

    def test_competition_aliases(self):
        assert COMPETITIONS["serie a"] == "Brasileirão Série A"
        assert COMPETITIONS["brasileirao"] == "Brasileirão Série A"
        assert COMPETITIONS["libertadores"] == "Copa Libertadores"
        assert COMPETITIONS["copa do brasil"] == "Copa do Brasil"
