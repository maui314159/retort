"""Unit tests for dataset loading and deduplication."""

from __future__ import annotations

from brazilian_soccer_mcp.data import (
    BRASILEIRAO_A,
    COPA_DO_BRASIL,
    LIBERTADORES,
)

EXPECTED_FILES = {
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
    "fifa_data.csv",
}


class TestLoadCoverage:
    def test_all_six_files_loaded(self, kb):
        assert EXPECTED_FILES <= set(kb.load_report)

    def test_match_volume(self, kb):
        # ~24k raw match rows minus cross-file duplicates.
        assert 15_000 <= len(kb.matches) <= 24_000

    def test_player_volume(self, kb):
        assert len(kb.players) == 18_207

    def test_duplicates_were_removed(self, kb):
        assert kb.load_report["*dedupe*"]["duplicates_dropped"] > 3_000

    def test_no_null_critical_fields(self, kb):
        m = kb.matches
        assert m["date"].notna().all()
        assert m["home_goals"].notna().all()
        assert m["away_goals"].notna().all()
        assert (m["home_key"] != "").all()
        assert (m["away_key"] != "").all()


class TestDedupe:
    def test_2019_serie_a_is_complete_and_unique(self, kb):
        season = kb.matches[
            (kb.matches["competition"] == BRASILEIRAO_A) & (kb.matches["season"] == 2019)
        ]
        # 20 teams, double round-robin = 380 fixtures.
        assert len(season) == 380
        assert not season.duplicated(subset=["home_key", "away_key"]).any()

    def test_same_fixture_not_double_counted(self, kb):
        # Flamengo played exactly 38 Série A matches in 2019.
        fla = kb.matches[
            (kb.matches["competition"] == BRASILEIRAO_A)
            & (kb.matches["season"] == 2019)
            & ((kb.matches["home_key"] == "flamengo") | (kb.matches["away_key"] == "flamengo"))
        ]
        assert len(fla) == 38


class TestCompetitions:
    def test_competition_set(self, kb):
        assert set(kb.competitions) == {
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        }

    def test_date_range(self, kb):
        assert kb.matches["date"].min().year == 2003
        assert kb.matches["date"].max().year == 2023

    def test_libertadores_loaded(self, kb):
        lib = kb.matches[kb.matches["competition"] == LIBERTADORES]
        assert len(lib) > 1_000

    def test_cup_loaded(self, kb):
        cup = kb.matches[kb.matches["competition"] == COPA_DO_BRASIL]
        assert len(cup) > 1_500


class TestDisplayNames:
    def test_utf8_display_names_present(self, kb):
        names = set(kb.matches["home_team"]) | set(kb.matches["away_team"])
        assert "São Paulo" in names
        assert "Grêmio" in names

    def test_canonical_display_overrides_variants(self, kb):
        names = set(kb.matches["home_team"]) | set(kb.matches["away_team"])
        assert "Athletico Paranaense" in names
        # The EC-prefixed BR-Football spelling must not leak into display.
        assert "EC Bahia" not in names


class TestExtendedStats:
    def test_br_football_corners_present(self, kb):
        assert kb.matches["home_corners"].notna().any()
