"""Unit tests for the data layer: loading, coverage and deduplication."""

from __future__ import annotations

EXPECTED_SOURCE_ROWS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "novo_campeonato_brasileiro.csv": 6886,
    "BR-Football-Dataset.csv": 10296,
    "fifa_data.csv": 18207,
}


class TestLoading:
    def test_all_six_files_load(self, store):
        assert store.source_row_counts == EXPECTED_SOURCE_ROWS

    def test_unified_match_count(self, store):
        # 23,954 raw match rows collapse to the deduplicated union.
        assert 16_000 <= len(store.matches) <= 18_000

    def test_all_competitions_present(self, store):
        assert set(store.competitions) == {
            "serie a", "serie b", "serie c", "copa do brasil", "copa libertadores",
        }

    def test_player_count(self, store):
        assert len(store.players) == 18207

    def test_utf8_names_load_correctly(self, store):
        assert "sao paulo" in store.teams
        assert "gremio" in store.teams
        assert "avai" in store.teams


class TestCoverage:
    def test_serie_a_seasons_span_2003_to_2023(self, store):
        seasons = store.seasons("serie a")
        assert seasons[0] == 2003
        assert seasons[-1] == 2023

    def test_libertadores_coverage(self, store):
        seasons = store.seasons("copa libertadores")
        assert seasons[0] == 2013
        assert seasons[-1] == 2022

    def test_serie_a_season_has_380_matches(self, store):
        df = store.matches
        season = df[(df["competition"] == "serie a") & (df["season"] == 2019)]
        assert len(season) == 380
        teams = set(season["home"]) | set(season["away"])
        assert len(teams) == 20


class TestDedupe:
    def test_no_duplicate_fixtures(self, store):
        df = store.matches[store.matches["home_goals"].notna()]
        key = (
            df["competition"] + df["season"].astype(str)
            + df["home"] + df["away"]
            + df["home_goals"].astype(str) + df["away_goals"].astype(str)
        )
        assert not key.duplicated().any()

    def test_cross_source_fixture_collapses(self, store):
        """The 2019-04-27 Flamengo 3-1 Cruzeiro match exists in three source
        files but must appear exactly once in the unified table."""
        df = store.matches
        hit = df[
            (df["home"] == "flamengo")
            & (df["away"] == "cruzeiro")
            & (df["competition"] == "serie a")
            & (df["season"] == 2019)
        ]
        assert len(hit) == 1
        row = hit.iloc[0]
        assert (int(row["home_goals"]), int(row["away_goals"])) == (3, 1)

    def test_same_score_date_shift_collapses(self, store):
        """Late kick-offs recorded on different dates across sources (UTC vs
        local) still dedupe: 2022 Série A has exactly 380 matches."""
        df = store.matches
        season = df[(df["competition"] == "serie a") & (df["season"] == 2022)]
        assert len(season) == 380

    def test_cancelled_chapecoense_match_removed(self, store):
        """The 2016 round-38 Chapecoense–Atlético-MG fixture was cancelled
        after the LaMia disaster (one source lists a phantom 0-0); it must
        not appear in the unified table at all."""
        df = store.matches
        hit = df[
            (df["home"] == "chapecoense")
            & (df["away"] == "atletico mineiro")
            & (df["season"] == 2016)
        ]
        assert len(hit) == 0
        season = df[(df["competition"] == "serie a") & (df["season"] == 2016)]
        assert len(season) == 379  # 380 rounds minus the cancelled fixture


class TestPlayers:
    def test_brazilian_players(self, store):
        br = store.players[store.players["nationality"] == "Brazil"]
        assert len(br) == 827

    def test_position_groups(self, store):
        groups = set(store.players["position_group"].dropna())
        assert groups == {"goalkeeper", "defender", "midfielder", "forward"}

    def test_ratings_are_numeric(self, store):
        neymar = store.players[store.players["name"] == "Neymar Jr"].iloc[0]
        assert int(neymar["overall"]) == 92
        assert neymar["club"] == "Paris Saint-Germain"
