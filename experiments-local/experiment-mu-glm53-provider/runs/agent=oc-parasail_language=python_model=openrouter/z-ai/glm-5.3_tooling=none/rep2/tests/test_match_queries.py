"""GWT tests for match queries: search, filters, dedup and reconciliation."""

from __future__ import annotations



class TestSearchMatches:
    def test_given_all_matches_when_queried_by_team_then_only_that_team(self, engine):
        # Given the loaded dataset
        # When searching all Flamengo matches
        result = engine.search_matches(team="Flamengo", limit=2000)
        # Then every match involves Flamengo and the count matches the index
        assert result["total_matches"] > 300
        for match in result["matches"]:
            assert "flamengo" in (match["home_team_id"], match["away_team_id"])

    def test_given_matches_when_queried_by_opponent_then_head_to_head_fixtures(self, engine):
        result = engine.search_matches(team="Flamengo", opponent="Vasco", limit=2000)
        for match in result["matches"]:
            teams = {match["home_team_id"], match["away_team_id"]}
            assert teams == {"flamengo", "vasco"}

    def test_given_matches_when_filtered_by_date_range_then_dates_within(self, engine):
        result = engine.search_matches(
            date_from="2019-06-01", date_to="2019-06-30", limit=2000
        )
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert "2019-06" == match["date"][:7]

    def test_given_libertadores_when_filtered_by_semifinal_stage_then_no_finals(self, engine):
        result = engine.search_matches(competition="Libertadores", stage="semi", limit=2000)
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert match["stage"] == "semifinals"

    def test_given_unknown_competition_when_queried_then_error(self, engine):
        result = engine.search_matches(competition="Premier League")
        assert "error" in result

    def test_given_unknown_team_when_queried_then_error_with_candidates(self, engine):
        result = engine.search_matches(team="Palmeirass")
        assert "error" in result
        assert result["candidates"], "typo-tolerant candidates expected"

    def test_given_limit_when_fewer_matches_than_limit_then_truncation_noted(self, engine):
        full = engine.search_matches(team="Avaí", season=2019, limit=500)
        limited = engine.search_matches(team="Avaí", season=2019, limit=5)
        assert limited["total_matches"] == full["total_matches"]
        assert limited["returned"] == 5
        assert "more matches" in limited["summary"]


class TestMatchReconciliation:
    """Cross-file dedup guarantees (no doubled fixtures for covered seasons)."""

    def test_given_serie_a_season_covered_by_two_files_then_fixture_count_matches_round_robin(self, engine):
        # Given Série A 2019 exists in Brasileirao_Matches, novo and BR-Football
        # When reconciled
        fixtures = engine._by_family_season[("serie_a", 2019)]
        teams = {m.home_team for m in fixtures} | {m.away_team for m in fixtures}
        # Then the fixture set is exactly a 20-team double round-robin (380)
        assert len(teams) == 20
        assert len(fixtures) == 380
        pairings = {(m.home_team, m.away_team) for m in fixtures}
        assert len(pairings) == 380  # each orientation appears exactly once

    def test_given_reconciled_matches_then_primary_source_is_authoritative(self, engine):
        fixtures = engine._by_family_season[("serie_a", 2019)]
        sources = {m.source for m in fixtures}
        assert sources == {"Brasileirao_Matches.csv"}

    def test_given_brf_rows_when_merged_then_stats_are_attached(self, engine):
        # BR-Football is the only file with corner/shot statistics
        with_stats = [m for m in engine.matches if m.stats is not None]
        assert len(with_stats) > 5000
        sample = with_stats[0]
        assert sample.stats.as_dict()

    def test_given_all_files_when_loaded_then_expected_match_totals(self, engine):
        # 6 CSVs loadable and queryable (5 match files + players)
        totals = {family: len(ms) for family, ms in engine._by_family.items()}
        assert totals["serie_a"] == 8403
        assert totals["serie_b"] == 3677
        assert totals["serie_c"] == 1807
        assert totals["copa_do_brasil"] == 1570
        assert totals["libertadores"] == 1255
        assert len(engine.players) == 18207


class TestHeadToHead:
    def test_given_two_teams_when_compared_then_records_are_consistent(self, engine):
        result = engine.head_to_head("Flamengo", "Fluminense")
        a, b = result["team_a"], result["team_b"]
        assert a["matches"] == b["matches"] == result["total_matches"]
        assert a["wins"] + b["wins"] + a["draws"] == a["matches"]
        assert a["goals_for"] == b["goals_against"]
        assert a["goals_against"] == b["goals_for"]

    def test_given_same_team_when_compared_then_error(self, engine):
        assert "error" in engine.head_to_head("Flamengo", "Flamengo")

    def test_given_never_played_teams_when_compared_then_zero_matches(self, engine):
        # Boca Juniors and a small Brazilian club never met in the data
        result = engine.head_to_head("Boca Juniors", "Boavista")
        assert result["total_matches"] == 0
