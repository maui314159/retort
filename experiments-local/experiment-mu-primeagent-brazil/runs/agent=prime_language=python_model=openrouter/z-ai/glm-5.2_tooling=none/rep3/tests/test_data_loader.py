"""
Context Block
=============

Module: tests.test_data_loader
Purpose: Tests for the unified data loader that reads and normalises
         all six Kaggle CSV datasets.
"""

from __future__ import annotations

from brazilian_soccer_mcp.data_loader import DataLoader, MatchRecord, PlayerRecord


class TestDataLoading:
    """Tests that all six CSV files are loaded and queryable."""

    def test_all_files_loaded(self, loader: DataLoader):
        """Given the data directory, all six CSVs are loaded."""
        assert len(loader.matches) > 0, "No matches loaded"
        assert len(loader.players) > 0, "No players loaded"

    def test_match_count_reasonable(self, loader: DataLoader):
        """Given all sources, the total match count is substantial."""
        # After deduplication, we expect well over 10k matches
        assert len(loader.matches) > 10000

    def test_player_count_reasonable(self, loader: DataLoader):
        """Given the FIFA dataset, the player count is ~18k."""
        assert len(loader.players) > 15000

    def test_brasileirao_loaded(self, loader: DataLoader):
        """Given the loader, Brasileirao matches are present."""
        bras = [m for m in loader.matches if m.competition == "Brasileirao"]
        assert len(bras) > 0

    def test_cup_loaded(self, loader: DataLoader):
        """Given the loader, Copa do Brasil matches are present."""
        cup = [m for m in loader.matches if m.competition == "Copa do Brasil"]
        assert len(cup) > 0

    def test_libertadores_loaded(self, loader: DataLoader):
        """Given the loader, Libertadores matches are present."""
        lib = [m for m in loader.matches if m.competition == "Copa Libertadores"]
        assert len(lib) > 0

    def test_br_football_loaded(self, loader: DataLoader):
        """Given the loader, BR-Football extended stats are present."""
        brf = [m for m in loader.matches if m.source_file == "BR-Football-Dataset.csv"]
        assert len(brf) > 0

    def test_historical_loaded(self, loader: DataLoader):
        """Given the loader, Historical Brasileirao (2003-2019) is present."""
        hist = [m for m in loader.matches if m.source_file == "novo_campeonato_brasileiro.csv"]
        assert len(hist) > 0

    def test_fifa_loaded(self, loader: DataLoader):
        """Given the loader, FIFA player data is present."""
        assert len(loader.players) > 15000

    def test_match_record_has_required_fields(self, loader: DataLoader):
        """Given a loaded match, it has all required fields."""
        m = loader.matches[0]
        assert isinstance(m, MatchRecord)
        assert m.match_id is not None
        assert m.home_team_key is not None
        assert m.away_team_key is not None
        assert m.competition is not None

    def test_player_record_has_required_fields(self, loader: DataLoader):
        """Given a loaded player, it has all required fields."""
        p = loader.players[0]
        assert isinstance(p, PlayerRecord)
        assert p.name is not None
        assert p.nationality is not None
        assert p.club is not None

    def test_to_dict_serializable(self, loader: DataLoader):
        """Given a match, to_dict produces a serialisable dict."""
        import json
        m = loader.matches[0]
        d = m.to_dict()
        # Should be JSON-serialisable
        json.dumps(d, default=str)

    def test_deduplication_reduces_overlap(self, loader: DataLoader):
        """Given overlapping datasets, duplicates are removed."""
        from collections import Counter
        # 2019 Brasileirao should not have double the matches
        c2019 = Counter(m.source_file for m in loader.matches
                         if m.competition == "Brasileirao" and m.season == 2019)
        total_2019 = sum(c2019.values())
        # A single season should have ~380 matches, not 760
        assert total_2019 < 760, f"Dedup should reduce from ~760, got {total_2019} (sources: {dict(c2019)})"

    def test_brazilian_players_present(self, loader: DataLoader):
        """Given the FIFA data, Brazilian players are present."""
        brazilians = [p for p in loader.players if p.nationality == "Brazil"]
        assert len(brazilians) > 100

    def test_all_competitions_present(self, loader: DataLoader):
        """Given the loader, all six competition types are present."""
        competitions = set(m.competition for m in loader.matches)
        assert "Brasileirao" in competitions
        assert "Copa do Brasil" in competitions
        assert "Copa Libertadores" in competitions
