"""
BDD GWT scenarios: dataset loading and the canonical match index.

Gherkin counterpart: ``tests/features/dataset.feature``.

Covers TASK.md "Success Criteria" -> "Data Coverage": all six CSVs are
loadable and queryable, cross-file queries work, team-name variations are
handled, and no fixture is double-counted across overlapping sources.
"""

from __future__ import annotations

from collections import Counter


class TestFileCoverage:
    def test_given_all_six_csvs_when_loaded_then_row_counts_match_sources(self, dataset):
        # Given the bundled Kaggle datasets
        # When the dataset is assembled
        # Then every file is loaded with its expected row count
        assert dataset.file_stats["Brasileirao_Matches"]["rows"] == 4180
        assert dataset.file_stats["Brazilian_Cup_Matches"]["rows"] == 1337
        assert dataset.file_stats["Libertadores_Matches"]["rows"] == 1255
        assert dataset.file_stats["novo_campeonato_brasileiro"]["rows"] == 6886
        assert dataset.file_stats["BR-Football-Dataset"]["rows"] == 10296
        assert dataset.file_stats["fifa_data"]["rows"] == 18207

    def test_given_the_match_files_when_loaded_then_all_rows_parsed(self, dataset):
        # Given 23,954 match rows across five files
        # When parsed
        # Then every row produced a Match record
        assert len(dataset.raw_matches) == 23954

    def test_given_the_fifa_file_when_loaded_then_players_have_core_fields(self, dataset):
        # Given the FIFA player database
        # When loaded
        # Then players carry name, nationality, ratings and club
        assert len(dataset.players) == 18207
        neymar = next(p for p in dataset.players if p.name == "Neymar Jr")
        assert neymar.nationality == "Brazil"
        assert neymar.overall == 92
        assert neymar.club == "Paris Saint-Germain"
        assert neymar.position == "LW"

    def test_given_utf8_sources_when_loaded_then_accents_preserved(self, dataset):
        # Given accented team spellings in the raw data
        # When loaded
        # Then variant spellings keep their UTF-8 form
        variants = {v for c in dataset.registry.all_clubs() for v in c.variant_counts}
        assert any("Grêmio" in v for v in variants)
        assert any("São Paulo" in v for v in variants)


class TestClubRegistry:
    def test_given_overlapping_spellings_when_finalized_then_one_club(self, dataset):
        # Given "Vasco", "Vasco da Gama-RJ" and "Vasco Da Gama RJ" across files
        # When the registry is finalized
        # Then they share a single club id
        club = dataset.registry.resolve_one("Vasco da Gama")
        assert club.id == "vasco|RJ"
        flamengo = dataset.registry.resolve_one("Flamengo")
        assert flamengo.id == "flamengo|RJ"

    def test_given_same_base_different_states_when_finalized_then_distinct(self, dataset):
        # Given Botafogo-RJ vs Botafogo-PB and América-MG vs América-RN
        # When resolved
        # Then the distinct clubs remain distinct
        assert dataset.registry.resolve_one("Botafogo-PB").id == "botafogo|PB"
        assert dataset.registry.resolve_one("América-RN").id == "america|RN"
        assert dataset.registry.resolve_one("América-MG").id == "america|MG"

    def test_given_bare_flamengo_when_resolved_then_prefers_the_giant(self, dataset):
        # Given "Flamengo" (also a small Piauí club exists in cup data)
        # When resolved without a state
        # Then the Rio de Janeiro club wins on dataset presence
        ranked = dataset.registry.resolve("Flamengo")
        assert ranked[0].id == "flamengo|RJ"
        assert all(c.id != "flamengo|PI" for c in ranked)

    def test_given_foreign_and_brazilian_river_plate_when_resolved_then_separate(self, dataset):
        # Given "River Plate" (ARG, Libertadores/FIFA) and "River Plate - SE"
        # When resolved
        # Then the Argentine giant is its own club, not folded into the SE minnow
        argentine = dataset.registry.resolve_one("River Plate")
        assert argentine.id == "riverplate|"
        assert argentine.player_count > 0  # FIFA players attached

    def test_given_every_canonical_match_when_built_then_clubs_resolved(self, dataset):
        # Given the canonical match index
        # When built
        # Then every match has both club ids attached
        assert all(m._home_club and m._away_club for m in dataset.matches)

    def test_given_fifa_clubs_when_joined_then_players_counted(self, dataset):
        # Given the FIFA club join
        # Then Grêmio carries its 20 Brazilian players
        gremio = dataset.registry.resolve_one("Grêmio")
        assert gremio.player_count == 20


class TestCanonicalIndex:
    def test_given_overlapping_sources_when_canonicalized_then_one_source_per_season(self, dataset):
        # Given three files covering overlapping Brasileirão seasons
        # When the canonical index is built
        # Then each (competition, season) uses exactly one source
        # and the documented timeline holds
        get = dataset.season_sources
        assert get[("Brasileirão Serie A", 2019)]["source"] == "Brasileirao_Matches"
        assert get[("Brasileirão Serie A", 2003)]["source"] == "novo_campeonato_brasileiro"
        assert get[("Brasileirão Serie A", 2023)]["source"] == "BR-Football-Dataset"
        assert get[("Copa do Brasil", 2019)]["source"] == "Brazilian_Cup_Matches"
        assert get[("Copa Libertadores", 2019)]["source"] == "Libertadores_Matches"

    def test_given_the_canonical_index_when_checked_then_no_duplicate_fixture(self, dataset):
        # Given overlapping match sources
        # When canonicalized
        # Then no (competition, season, date, home, away) fixture repeats
        seen = Counter()
        for m in dataset.matches:
            if m.date is None or not m.has_score:
                continue
            seen[(m.competition, m.season, m.date, m._home_club, m._away_club)] += 1
        duplicates = {k: v for k, v in seen.items() if v > 1}
        assert not duplicates

    def test_given_a_complete_season_when_counted_then_full_round_robin(self, dataset):
        # Given the 2019 Brasileirão (20 teams)
        # When counting canonical matches
        # Then all 380 fixtures are present with scores
        matches = [m for m in dataset.matches if m.competition == "Brasileirão Serie A" and m.season == 2019]
        assert len(matches) == 380
        assert all(m.has_score for m in matches)

    def test_given_scores_or_placeholders_when_parsed_then_flags_set(self, dataset):
        # Given rows with 'NA' goals (2022 final round, 2021 cup rounds)
        # When loaded
        # Then they are kept but flagged as unscored
        unscored = [m for m in dataset.matches if not m.has_score]
        assert unscored, "expected placeholder rows to be retained"
        assert all(m.score == "N/A" for m in unscored)
        assert all(m.winner is None for m in unscored)

    def test_given_extended_stats_when_joined_then_attached_to_canonical(self, dataset):
        # Given BR-Football corners/shots/attacks
        # When the canonical index is built
        # Then a share of canonical matches carries extended statistics
        with_stats = [m for m in dataset.matches if m.stats is not None]
        assert len(with_stats) > 2000
        sample = with_stats[0].stats
        assert sample is not None
        assert sample.kickoff_time is not None
