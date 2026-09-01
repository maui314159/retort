# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# BDD tests for the data loader. Verifies every CSV file is loadable, row
# counts are plausible, and normalization produced non-empty keys.
# --------------------------------------------------------------------------- #
"""BDD scenarios for the Kaggle CSV loader."""

from __future__ import annotations

from brazilian_soccer_mcp.data_loader import (
    _BR_FOOTBALL_FILE,
    _BRASILEIRAO_FILE,
    _CUP_FILE,
    _FIFA_FILE,
    _HISTORICAL_FILE,
    _LIBERTADORES_FILE,
    DEFAULT_DATA_DIR,
    DataLoader,
)
from brazilian_soccer_mcp.models import Match, Player


class TestDataLoader:
    def test_all_six_source_files_exist(self):
        # Given the data directory
        # When I check for the 6 source files
        # Then all of them exist
        import os
        for fname in (
            _BRASILEIRAO_FILE, _CUP_FILE, _LIBERTADORES_FILE,
            _BR_FOOTBALL_FILE, _HISTORICAL_FILE, _FIFA_FILE,
        ):
            assert os.path.exists(os.path.join(DEFAULT_DATA_DIR, fname)), fname

    def test_load_all_populates_matches_and_players(self, loader: DataLoader):
        # Given a DataLoader
        # When load_all() has run
        # Then both matches and players are populated
        assert len(loader.matches) > 0
        assert len(loader.players) > 0

    def test_match_counts_plausible(self, loader: DataLoader):
        # Given the loaded matches
        # When I check the total
        # Then it is in the plausible 20k-25k range (sum of source rows)
        assert 20000 <= len(loader.matches) <= 25000

    def test_player_count_plausible(self, loader: DataLoader):
        # Given the loaded players
        # When I check the total
        # Then it is near the spec'd 18,207
        assert 18000 <= len(loader.players) <= 19000

    def test_every_match_has_competition_and_team_keys(self, loader: DataLoader):
        # Given the loaded matches
        # When I inspect each match
        # Then it has a non-empty competition string and canonical team keys
        for m in loader.matches[:500]:  # sample for speed
            assert m.competition, m
            assert m.home_team_key, m
            assert m.away_team_key, m

    def test_competitions_present(self, loader: DataLoader):
        # Given the loaded matches
        # When I collect the competition names
        # Then the 3 named competitions from the spec are present
        comps = {m.competition for m in loader.matches}
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_matches_are_match_dataclass_instances(self, loader: DataLoader):
        assert isinstance(loader.matches[0], Match)
        assert isinstance(loader.players[0], Player)

    def test_historical_brasileirao_has_stadium(self, loader: DataLoader):
        # Given matches from the historical (2003-2019) file
        # When I find one with a stadium
        # Then at least one has a non-null stadium field
        hist = [m for m in loader.matches if m.source_file == _HISTORICAL_FILE]
        assert hist
        assert any(m.stadium for m in hist)

    def test_libertadores_has_stage(self, loader: DataLoader):
        # Given matches from the Libertadores file
        # When I inspect one
        # Then it carries the 'stage' field
        lib = [m for m in loader.matches if m.source_file == _LIBERTADORES_FILE]
        assert lib
        assert any(m.stage for m in lib)

    def test_fifa_players_have_overall_rating(self, loader: DataLoader):
        # Given the loaded FIFA players
        # When I sample them
        # Then most have a non-null overall rating
        with_rating = sum(1 for p in loader.players if p.overall is not None)
        assert with_rating > len(loader.players) * 0.9

    def test_stats_summary_shape(self, loader: DataLoader):
        # Given a loaded DataLoader
        # When I call stats()
        # Then it returns the expected keys
        s = loader.stats()
        assert "matches_total" in s
        assert "players_total" in s
        assert "matches_by_competition" in s
        assert "source_files" in s
        assert len(s["source_files"]) == 6
