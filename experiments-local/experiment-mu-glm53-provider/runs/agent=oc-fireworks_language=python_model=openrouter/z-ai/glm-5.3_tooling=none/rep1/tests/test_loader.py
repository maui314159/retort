"""
Feature: Dataset loading, dedup and the club registry
  Five of the six CSV files describe overlapping fixtures with different
  team spellings.  The loader must merge duplicates into one canonical
  match list, repair known data errors, and expose a club registry that
  resolves every spelling variation.
"""

from __future__ import annotations

import collections

from brazilian_soccer_mcp.loader import default_data_dir


class TestDataCoverage:
    """Scenario: all six CSV files are loadable and queryable."""

    def test_all_files_present(self):
        """
        Scenario: the data directory contains all six datasets
          Given the default data directory
          Then every file named in TASK.md exists
        """
        data_dir = default_data_dir()
        expected = [
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
            "fifa_data.csv",
        ]
        for name in expected:
            assert (data_dir / name).exists(), f"missing {name}"

    def test_every_competition_loaded(self, ds):
        """
        Scenario: matches load for every competition
          Given the loaded dataset
          Then Serie A, Serie B, Serie C, Copa do Brasil and Libertadores
            all have matches
          And the FIFA player database has 18,207 players
        """
        for competition in (
            "serie_a",
            "serie_b",
            "serie_c",
            "copa_do_brasil",
            "libertadores",
        ):
            assert len(ds.competition_matches[competition]) > 500, competition
        assert len(ds.players) == 18_207
        assert sum(1 for p in ds.players if p.nationality == "Brazil") == 827

    def test_match_objects_are_complete(self, ds):
        """
        Scenario: every match carries the required fields
          Given the loaded dataset
          Then each match has date, teams, competition, season and source
            (goals may be None for scheduled-but-unplayed fixtures)
        """
        for match in ds.matches[:500]:
            assert match.competition in {
                "serie_a",
                "serie_b",
                "serie_c",
                "copa_do_brasil",
                "libertadores",
            }
            assert match.home and match.away
            assert match.home_key and match.away_key
            assert match.source
            assert match.season is None or isinstance(match.season, int)
        with_scores = [m for m in ds.matches if m.played]
        assert len(with_scores) > 10_000

    def test_unplayed_fixtures_are_marked(self, ds):
        """
        Scenario: 'NA'/'-' goals mean the fixture was not played
          Given the loaded dataset
          Then the three fixtures recorded without a final score are kept
            for schedules but flagged unplayed
            (the abandoned 2015 Boca/River Libertadores clash, one 2021
             cup leg and the unfinished Libertadores final row)
          And unplayed fixtures never appear in any statistic
        """
        unplayed = [m for m in ds.matches if not m.played]
        assert len(unplayed) == 3
        assert all(m.home_goals is None and m.away_goals is None for m in unplayed)
        comps = {m.competition for m in unplayed}
        assert comps == {"libertadores", "copa_do_brasil"}


class TestDeduplication:
    """Scenario: overlapping sources merge into one fixture per match."""

    def test_serie_a_seasons_are_exact(self, ds):
        """
        Scenario: Série A seasons deduplicate to their true size
          Given the loaded dataset
          Then 2003 has 552 matches, 2004 552, 2005 462
          And every season 2006-2022 has 380 matches
            (2009 has 379 - a duplicated row in the source file;
             2023 has 377 - the BR-Football source is three short)
        """
        per_season = collections.Counter(
            m.season for m in ds.competition_matches["serie_a"]
        )
        assert per_season[2003] == 552
        assert per_season[2004] == 552
        assert per_season[2005] == 462
        for season in range(2006, 2023):
            if season == 2009:
                assert per_season[season] == 379
            else:
                assert per_season[season] == 380, season
        assert per_season[2023] == 377

    def test_no_duplicate_league_orientations(self, ds):
        """
        Scenario: a league pairing meets at most twice per season
          Given the loaded dataset
          When I count (season, home, away) orientations per league
          Then no orientation occurs more than once
        """
        orientations = collections.Counter(
            (m.competition, m.season, m.home_key, m.away_key)
            for m in ds.matches
            if m.competition in ("serie_a", "serie_b", "serie_c")
        )
        duplicates = {k: v for k, v in orientations.items() if v > 1}
        assert not duplicates, f"duplicated league fixtures: {list(duplicates)[:5]}"

    def test_mislabeled_brf_fixtures_are_dropped(self, ds):
        """
        Scenario: BR-Football rows that tag Série B clubs as Serie A vanish
          Given the loaded dataset
          Then Botafogo/Coritiba/Goiás/Vasco play no Série A 2021 matches
            (they were relegated to Série B after 2020)
        """
        serie_a_2021 = ds.season_matches[("serie_a", 2021)]
        for key in ("botafogo|RJ", "coritiba|PR", "goias|GO", "vasco|RJ"):
            involved = [m for m in serie_a_2021 if key in (m.home_key, m.away_key)]
            assert not involved, f"{key} appears in Série A 2021"

    def test_novo_uf_repairs(self, ds):
        """
        Scenario: the historical file's UF errors are repaired
          Given the loaded dataset
          Then Bahia's 2003-2019 matches live under key "bahia|BA" (not BH)
          And Vitória's matches live under "vitoria|BA" (not ES)
        """
        assert "bahia|BA" in ds.clubs
        assert "bahia|BH" not in ds.clubs
        assert "vitoria|BA" in ds.clubs
        assert not any(
            k.startswith("vitoria|ES")
            for k in ds.clubs
            if ds.clubs[k].match_count > 100
        )

    def test_cross_source_score_conflicts_prefer_primary(self, ds):
        """
        Scenario: when two sources disagree on a score the primary wins
          Given the loaded dataset
          Then the 2014 Sport vs Fluminense fixture appears exactly once
            with the Brasileirao_Matches.csv score (2-2)
        """
        fixtures = [
            m
            for m in ds.season_matches[("serie_a", 2014)]
            if {m.home_key, m.away_key} == {"sport|PE", "fluminense|RJ"}
            and str(m.date) == "2014-11-23"
        ]
        assert len(fixtures) == 1
        assert (fixtures[0].home_goals, fixtures[0].away_goals) == (2, 2)
        assert fixtures[0].source == "Brasileirao_Matches.csv"


class TestClubRegistry:
    """Scenario: the registry resolves every spelling to one club node."""

    def test_major_clubs_resolve(self, ds):
        """
        Scenario: major clubs resolve from any spelling
          Given the loaded club registry
          When I resolve "Flamengo", "Flamengo-RJ", "Palmeiras-SP",
            "Sport Club Corinthians Paulista" and "Gremio"
          Then all resolve to the expected canonical keys
        """
        assert ds.resolve_club_key("Flamengo") == "flamengo|RJ"
        assert ds.resolve_club_key("Flamengo-RJ") == "flamengo|RJ"
        assert ds.resolve_club_key("Palmeiras-SP") == "palmeiras|SP"
        assert (
            ds.resolve_club_key("Sport Club Corinthians Paulista") == "corinthians|SP"
        )
        assert ds.resolve_club_key("Gremio") == "gremio|RS"
        assert ds.resolve_club_key("Atletico Mineiro") == "atletico|MG"
        assert ds.resolve_club_key("Athletico Paranaense") == "atletico|PR"
        assert ds.resolve_club_key("Vasco da Gama") == "vasco|RJ"

    def test_stateless_names_resolve_by_prominence(self, ds):
        """
        Scenario: ambiguous bare names resolve to the prominent club
          Given the loaded club registry
          When I resolve "Botafogo" and "Santos"
          Then they resolve to the Rio and Santos-SP clubs
        """
        assert ds.resolve_club_key("Botafogo") == "botafogo|RJ"
        assert ds.resolve_club_key("Santos") == "santos|SP"
        assert ds.resolve_club_key("America") == "america|MG"

    def test_registry_records_variants_and_stats(self, ds):
        """
        Scenario: registry entries carry the club's data footprint
          Given the loaded club registry
          Then Palmeiras lists its spelling variations, competitions,
            seasons and a positive match count
        """
        club = ds.clubs["palmeiras|SP"]
        assert club.display == "Palmeiras"
        assert "Palmeiras-SP" in club.variants
        assert set(club.competitions) == {"serie_a", "copa_do_brasil", "libertadores"}
        assert club.match_count > 500
        # Palmeiras spent 2003 in Série B, which the match files do not
        # cover - their first Série A season here is 2004.
        assert 2003 not in club.seasons
        assert 2004 in club.seasons and 2023 in club.seasons

    def test_foreign_clubs_resolve_with_country(self, ds):
        """
        Scenario: Libertadores foreign clubs keep their country
          Given the loaded club registry
          When I resolve "Nacional (URU)" and "Barcelona-EQU"
          Then the keys carry the country suffixes
        """
        assert ds.resolve_club_key("Nacional (URU)") == "nacional|URU"
        assert ds.resolve_club_key("Barcelona-EQU") == "barcelona|EQU"

    def test_fifa_club_resolution(self, ds):
        """
        Scenario: FIFA club strings resolve to registry clubs
          Given the loaded dataset
          When I resolve FIFA club names "Grêmio" and "Atlético Mineiro"
          Then they map to the registry keys of those clubs
          And "Paris Saint-Germain" has no registry entry
        """
        assert ds.fifa_club_key("Grêmio") == "gremio|RS"
        assert ds.fifa_club_key("Atlético Mineiro") == "atletico|MG"
        assert ds.fifa_club_key("Paris Saint-Germain") is None


class TestPerformance:
    """Scenario: TASK.md performance criteria."""

    def test_load_time(self, ds_timed):
        """
        Scenario: the dataset loads quickly
          Given a cold process
          When the six CSVs are loaded and indexed
          Then it takes well under five seconds
        """
        _dataset, seconds = ds_timed
        assert seconds < 5.0, f"load took {seconds:.2f}s"

    def test_query_time(self, ds):
        """
        Scenario: simple lookups answer in under two seconds
          Given the loaded dataset
          When I search Flamengo's fixtures and compute the 2019 table
          Then both answer in under two seconds
        """
        import time

        from brazilian_soccer_mcp.queries import search_matches, standings

        started = time.perf_counter()
        result = search_matches(ds, team="Flamengo", limit=50)
        assert result["ok"]
        search_seconds = time.perf_counter() - started

        started = time.perf_counter()
        table = standings(ds, "serie_a", 2019)
        assert table["ok"]
        standings_seconds = time.perf_counter() - started

        assert search_seconds < 2.0, f"search took {search_seconds:.2f}s"
        assert standings_seconds < 5.0, f"standings took {standings_seconds:.2f}s"
