"""Tests for dataset loading, normalization, and deduplication (R2)."""

from collections import Counter
from datetime import date

import pytest

from brazilian_soccer_mcp.data_loader import Dataset
from brazilian_soccer_mcp.normalize import identity_key, parse_date

EXPECTED_SOURCES = {
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
}

EXPECTED_COMPETITIONS = {
    "Brasileirão",
    "Copa do Brasil",
    "Libertadores",
    "Serie B",
    "Serie C",
}


class TestLoading:
    def test_matches_loaded(self, dataset: Dataset):
        assert len(dataset.matches) > 10_000

    def test_players_loaded(self, dataset: Dataset):
        assert len(dataset.players) == 18_207

    def test_all_five_match_files_used(self, dataset: Dataset):
        sources = {m.source for m in dataset.matches}
        assert EXPECTED_SOURCES <= sources

    def test_all_competitions_present(self, dataset: Dataset):
        assert EXPECTED_COMPETITIONS <= set(dataset.competitions())

    def test_match_fields_populated(self, dataset: Dataset):
        sample = dataset.matches[0]
        assert sample.home_team and sample.away_team
        assert sample.competition in EXPECTED_COMPETITIONS | {"Copa do Brasil"}
        assert sample.date is None or isinstance(sample.date, str)

    def test_scores_parsed_where_available(self, dataset: Dataset):
        with_goals = [m for m in dataset.matches if m.home_goals is not None]
        assert len(with_goals) > 10_000
        assert all(0 <= m.home_goals <= 12 for m in with_goals[:1000])

    def test_dates_parsed_as_iso(self, dataset: Dataset):
        dated = [m for m in dataset.matches if m.date]
        assert len(dated) > 10_000
        for match in dated[:2000]:
            assert parse_date(match.date) is not None

    def test_player_fields_populated(self, dataset: Dataset):
        player = dataset.players[0]
        assert player.name
        assert player.nationality
        assert 40 <= player.overall <= 99
        assert isinstance(player.skills, dict)


class TestTeamNormalization:
    def test_state_suffixes_removed_from_match_data(self, dataset: Dataset):
        for match in dataset.matches[:5000]:
            assert not match.home_team.endswith(("-SP", "-RJ", "-MG"))

    def test_resolve_team_variants(self, dataset: Dataset):
        assert dataset.resolve_team("Palmeiras-SP") == dataset.resolve_team("Palmeiras")
        assert dataset.resolve_team("Sao Paulo") == dataset.resolve_team("São Paulo")
        assert dataset.resolve_team("Fortaleza EC") == dataset.resolve_team("Fortaleza")

    def test_matches_for_team(self, dataset: Dataset):
        flamengo = dataset.matches_for_team("Flamengo")
        assert flamengo
        for match in flamengo:
            assert "Flamengo" in (match.home_team, match.away_team)

    def test_team_index_covers_both_sides(self, dataset: Dataset):
        canonical = dataset.resolve_team("Santos")
        appearances = dataset.matches_for_team(canonical)
        roles = Counter(
            "home" if m.home_team == canonical else "away" for m in appearances
        )
        assert roles["home"] > 0 and roles["away"] > 0


class TestDeduplication:
    def _fixture_key(self, match):
        return (
            match.competition,
            match.season,
            identity_key(match.home_team),
            identity_key(match.away_team),
        )

    def test_no_same_fixture_within_window(self, dataset: Dataset):
        """Same ordered pairing in one competition+season must be unique
        within a few days (overlapping sources report one fixture once)."""
        seen: dict[tuple, date] = {}
        for match in dataset.matches:
            if not match.date or match.season is None:
                continue
            key = self._fixture_key(match)
            day = parse_date(match.date)
            previous = seen.get(key)
            if previous is not None and day is not None:
                gap = abs((day - previous).days)
                assert gap > Dataset.DEDUP_WINDOW_DAYS, (
                    f"duplicate fixture {key} on {previous} and {day}"
                )
            seen[key] = day

    def test_league_season_has_expected_volume(self, dataset: Dataset):
        """2019 Brasileirão is a complete 20-team double round-robin."""
        matches = [
            m for m in dataset.matches
            if m.competition == "Brasileirão" and m.season == 2019
        ]
        flamengo_games = [
            m for m in matches if "Flamengo" in (m.home_team, m.away_team)
        ]
        assert len(flamengo_games) == 38


class TestDiscovery:
    def test_competitions_report_seasons(self, dataset: Dataset):
        info = dataset.competitions()
        for entry in info.values():
            assert entry["matches"] > 0
            assert isinstance(entry["seasons"], list)

    def test_teams_listing(self, dataset: Dataset):
        teams = dataset.teams()
        assert "Flamengo" in teams
        assert all(count > 0 for count in teams.values())

    def test_missing_data_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Dataset(tmp_path / "does-not-exist")
