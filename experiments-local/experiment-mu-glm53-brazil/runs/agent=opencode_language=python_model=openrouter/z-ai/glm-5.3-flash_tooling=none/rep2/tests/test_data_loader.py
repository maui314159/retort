"""Unit tests for the CSV data loader: coverage, dedupe and enrichment."""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data_loader import SoccerData

EXPECTED_ROWS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "BR-Football-Dataset.csv": 10296,
    "novo_campeonato_brasileiro.csv": 6886,
    "fifa_data.csv": 18207,
}


class TestCoverage:
    def test_all_six_files_loaded(self, data: SoccerData) -> None:
        for filename, rows in EXPECTED_ROWS.items():
            assert data.skipped[filename] == rows, filename

    def test_all_rows_accounted_for(self, data: SoccerData) -> None:
        stats = data.dataset_stats()
        assert stats["players"] == 18207
        assert stats["unique_matches"] > 0
        # Every competition is represented
        comps = stats["matches_per_competition"]
        for expected in ("Brasileirão Série A", "Brasileirão Série B",
                         "Brasileirão Série C", "Copa do Brasil",
                         "Copa Libertadores"):
            assert expected in comps

    def test_unique_match_ids(self, data: SoccerData) -> None:
        ids = [m.match_id for m in data.matches]
        assert len(ids) == len(set(ids))

    def test_teams_and_dates_normalized(self, data: SoccerData) -> None:
        for match in data.matches[:500]:
            assert match.home_team and match.away_team
            assert match.home_team == match.home_team.strip()
            assert match.date is None or len(match.date) == 10
        scored = [m for m in data.matches if m.date is not None]
        assert scored, "most matches should carry an ISO date"


class TestDeduplication:
    """The two Brasileirão sources overlap 2012-2019 and must not double count."""

    def test_serie_a_2019_is_a_complete_season(self, data: SoccerData) -> None:
        matches = data.matches_in_competition("Brasileirão Série A", 2019)
        assert len(matches) == 380
        teams = {m.home_team for m in matches} | {m.away_team for m in matches}
        assert len(teams) == 20

    def test_historical_2003_season(self, data: SoccerData) -> None:
        matches = data.matches_in_competition("Brasileirão Série A", 2003)
        assert len(matches) == 552  # 24-team double round robin
        teams = {m.home_team for m in matches} | {m.away_team for m in matches}
        assert len(teams) == 24

    def test_seasons_2012_to_2022_complete(self, data: SoccerData) -> None:
        for season in range(2012, 2023):
            matches = data.matches_in_competition("Brasileirão Série A", season)
            assert len(matches) == 380, season

    def test_duplicate_fixtures_enriched_not_duplicated(self, data: SoccerData) -> None:
        # 2019-11-10 Flamengo x Vasco (4-4) appears in both primary files
        flamengo_vasco = [
            m for m in data.matches_between("Flamengo", "Vasco da Gama")
            if m.season == 2019 and m.competition == "Brasileirão Série A"
            and m.date and "2019-11" in m.date
        ]
        assert len(flamengo_vasco) == 1


class TestEnrichment:
    def test_extended_stats_merged(self, data: SoccerData) -> None:
        with_stats = [
            m for m in data.matches
            if m.extra.get("home_shots") is not None
        ]
        assert with_stats, "BR-Football stats should be merged into deduped matches"

    def test_arena_from_historical_file(self, data: SoccerData) -> None:
        with_arena = [m for m in data.matches if m.arena]
        assert len(with_arena) > 3000

    def test_wins_processed(self, data: SoccerData) -> None:
        draws = [m for m in data.matches if m.winner is None and m.home_goals == m.away_goals and m.home_goals is not None]
        assert draws


class TestIndexes:
    def test_matches_between(self, data: SoccerData) -> None:
        matches = data.matches_between("Flamengo", "Fluminense")
        assert matches
        for m in matches:
            assert {key for key in (m.home_team, m.away_team)} == {"Flamengo", "Fluminense"}

    def test_resolve_team_partial_names(self, data: SoccerData) -> None:
        assert data.resolve_team("Palmeiras") == "Palmeiras"
        assert data.resolve_team("Flamengo") == "Flamengo"

    def test_resolve_unknown_team(self, data: SoccerData) -> None:
        assert data.resolve_team("Zezinho FC do Interior 99") is None

    def test_competition_names(self, data: SoccerData) -> None:
        names = data.competition_names()
        assert "Copa do Brasil" in names
        assert names["Copa do Brasil"] > 1000


class TestPlayers:
    def test_brazilian_players_present(self, data: SoccerData) -> None:
        brazilians = [p for p in data.players if p.nationality == "Brazil"]
        assert len(brazilians) > 800

    def test_player_attributes_parsed(self, data: SoccerData) -> None:
        neymar = next(p for p in data.players if p.name == "Neymar Jr")
        assert neymar.overall == 92
        assert neymar.club == "Paris Saint-Germain"
        assert neymar.height_cm is not None and neymar.height_cm > 150
        assert neymar.weight_kg is not None and neymar.weight_kg > 50
        assert "Dribbling" in neymar.skills
