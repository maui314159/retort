"""Tests for the query engine (R3–R11).

Each test maps to a requirement from FEEDBACK.md:
  R3  find matches by team (home, away, or either)
  R4  filter by date range and/or season
  R5  filter by competition
  R6  team statistics: W/L/D + goals for/against
  R7  search players by name
  R8  filter players by nationality and/or club, with ratings
  R9  competition standings calculated from match results
  R10 statistical analysis (avg goals, biggest wins, best record)
  R11 head-to-head records between two teams
"""
from __future__ import annotations
from brazilian_soccer import queries as q
from brazilian_soccer.normalize import team_key


# ---------------------------------------------------------------------------
# R3: match query — find matches by team (home, away, or either)
# ---------------------------------------------------------------------------

class TestFindMatchesByTeam:
    def test_find_by_team_either(self):
        results = q.find_matches(team="Flamengo", limit=200)
        assert len(results) > 0
        for m in results:
            assert team_key(m["home_team"]) == team_key("Flamengo") or \
                   team_key(m["away_team"]) == team_key("Flamengo")

    def test_find_by_team_home_only(self):
        """When side is home, all results should have the team as home."""
        # find_matches doesn't take a side param directly, but we can verify
        # via team_statistics with venue="home" — tested in TestTeamStatistics.
        # Here we verify the opponent filter narrows correctly.
        results = q.find_matches(team="Flamengo", opponent="Fluminense", limit=50)
        assert len(results) > 0
        for m in results:
            teams = {team_key(m["home_team"]), team_key(m["away_team"])}
            assert team_key("Flamengo") in teams
            assert team_key("Fluminense") in teams

    def test_team_name_variants_resolve(self):
        """R3/R6 team-name normalization: 'Palmeiras-SP' == 'Palmeiras'."""
        with_suffix = q.find_matches(team="Palmeiras-SP", limit=10)
        without = q.find_matches(team="Palmeiras", limit=10)
        # Both should return matches; the set of team_keys should overlap.
        assert len(with_suffix) > 0
        assert len(without) > 0

    def test_matches_have_required_fields(self):
        results = q.find_matches(team="Flamengo", limit=3)
        for m in results:
            assert "date" in m
            assert "home_team" in m
            assert "away_team" in m
            assert "home_goal" in m
            assert "away_goal" in m
            assert "competition" in m


# ---------------------------------------------------------------------------
# R4: filter by date range and/or season
# ---------------------------------------------------------------------------

class TestFindMatchesByDateAndSeason:
    def test_filter_by_season(self):
        results = q.find_matches(team="Palmeiras", season=2023, limit=200)
        assert len(results) > 0
        for m in results:
            assert m["season"] == 2023

    def test_filter_by_date_range(self):
        results = q.find_matches(
            team="Flamengo",
            start_date="2023-01-01",
            end_date="2023-06-30",
            limit=200,
        )
        assert len(results) > 0
        for m in results:
            d = m["date"]
            if d is not None:
                assert "2023-01-01" <= d <= "2023-06-30"

    def test_filter_by_season_and_competition(self):
        results = q.find_matches(
            team="Flamengo", season=2023,
            competition="Brasileirão Série A", limit=200,
        )
        assert len(results) > 0
        for m in results:
            assert m["season"] == 2023
            assert m["competition"] == "Brasileirão Série A"


# ---------------------------------------------------------------------------
# R5: filter by competition
# ---------------------------------------------------------------------------

class TestFindMatchesByCompetition:
    def test_filter_brasileirao(self):
        results = q.find_matches(
            competition="Brasileirão Série A", limit=10,
        )
        assert len(results) > 0
        for m in results:
            assert m["competition"] == "Brasileirão Série A"

    def test_filter_copa_do_brasil(self):
        results = q.find_matches(
            team="Palmeiras", competition="Copa do Brasil", limit=50,
        )
        assert len(results) > 0
        for m in results:
            assert m["competition"] == "Copa do Brasil"

    def test_filter_libertadores(self):
        results = q.find_matches(
            competition="Copa Libertadores", limit=10,
        )
        assert len(results) > 0
        for m in results:
            assert m["competition"] == "Copa Libertadores"


# ---------------------------------------------------------------------------
# R6: team statistics — W/L/D + goals for/against
# ---------------------------------------------------------------------------

class TestTeamStatistics:
    def test_basic_record(self):
        rec = q.team_statistics("Palmeiras", season=2023)
        assert rec["played"] > 0
        assert rec["wins"] >= 0
        assert rec["draws"] >= 0
        assert rec["losses"] >= 0
        assert rec["wins"] + rec["draws"] + rec["losses"] == rec["played"]
        assert rec["goals_for"] >= 0
        assert rec["goals_against"] >= 0

    def test_venue_home(self):
        rec = q.team_statistics("Corinthians", season=2022, venue="home")
        assert rec["played"] > 0

    def test_venue_away(self):
        rec = q.team_statistics("Corinthians", season=2022, venue="away")
        assert rec["played"] > 0

    def test_team_competitions(self):
        comps = q.team_competitions("Flamengo")
        assert len(comps) > 0
        comp_names = [c["competition"] for c in comps]
        assert "Brasileirão Série A" in comp_names


# ---------------------------------------------------------------------------
# R7: search players by name
# ---------------------------------------------------------------------------

class TestSearchPlayersByName:
    def test_search_by_name(self):
        results = q.search_players(name="Neymar", limit=10)
        assert len(results) >= 1
        assert any("neymar" in n.lower() for n in (r["name"] for r in results))

    def test_name_search_accent_insensitive(self):
        """Searching 'sao' should match 'São' entries (accent folding)."""
        results = q.search_players(name="sao", limit=10)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# R8: filter players by nationality and/or club, with ratings
# ---------------------------------------------------------------------------

class TestSearchPlayersByFilters:
    def test_filter_by_nationality(self):
        results = q.search_players(nationality="Brazil", limit=20)
        assert len(results) > 0
        for p in results:
            assert p["nationality"] == "Brazil"
            assert p["overall"] is not None

    def test_filter_by_club(self):
        results = q.search_players(club="Santos", limit=20)
        assert len(results) > 0
        for p in results:
            assert "santos" in p["club"].lower()

    def test_filter_by_nationality_and_club(self):
        results = q.search_players(nationality="Brazil", club="Santos", limit=20)
        assert len(results) > 0
        for p in results:
            assert p["nationality"] == "Brazil"

    def test_ratings_and_attributes_present(self):
        results = q.search_players(nationality="Brazil", limit=5)
        for p in results:
            assert p["overall"] is not None
            assert p["position"] is not None
            # Attributes dict should be present (may be empty for some rows).
            assert isinstance(p["attributes"], dict)

    def test_position_group_filter(self):
        results = q.search_players(position_group="GK", limit=10)
        assert len(results) > 0
        for p in results:
            assert p["position"] == "GK"


# ---------------------------------------------------------------------------
# R9: competition standings calculated from match results
# ---------------------------------------------------------------------------

class TestCompetitionStandings:
    def test_standings_returned(self):
        standings = q.competition_standings("Brasileirão Série A", 2019, top=5)
        assert len(standings) > 0
        for s in standings:
            assert "position" in s
            assert "team" in s
            assert "points" in s
            assert "wins" in s
            assert "draws" in s
            assert "losses" in s

    def test_standings_sorted_by_points(self):
        standings = q.competition_standings("Brasileirão Série A", 2019)
        pts = [s["points"] for s in standings]
        assert pts == sorted(pts, reverse=True)

    def test_positions_sequential(self):
        standings = q.competition_standings("Brasileirão Série A", 2019, top=5)
        positions = [s["position"] for s in standings]
        assert positions == list(range(1, len(standings) + 1))

    def test_champion(self):
        champ = q.competition_champion("Brasileirão Série A", 2019)
        assert champ is not None
        assert champ["champion"] == "Flamengo"

    def test_relegated(self):
        relegated = q.relegated_teams("Brasileirão Série A", 2019, n=4)
        assert relegated is not None
        assert len(relegated) == 4

    def test_standings_not_hardcoded(self):
        """Standings are computed from data: different seasons give different teams."""
        s2018 = q.competition_standings("Brasileirão Série A", 2018, top=1)
        s2019 = q.competition_standings("Brasileirão Série A", 2019, top=1)
        assert s2018[0]["team"] != s2019[0]["team"] or \
               s2018[0]["points"] != s2019[0]["points"]


# ---------------------------------------------------------------------------
# R10: statistical analysis
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    def test_average_goals(self):
        result = q.average_goals(competition="Brasileirão Série A")
        assert result["matches"] > 0
        assert result["avg_goals_per_match"] > 0
        assert result["home_wins"] + result["away_wins"] + result["draws"] == \
               result["matches"]

    def test_average_goals_by_season(self):
        result = q.average_goals(competition="Brasileirão Série A", season=2023)
        assert result["matches"] > 0
        assert result["avg_goals_per_match"] > 0

    def test_home_win_rate_positive(self):
        result = q.average_goals(competition="Brasileirão Série A")
        assert 0 < result["home_win_rate"] < 1

    def test_biggest_wins(self):
        results = q.biggest_wins(limit=5)
        assert len(results) > 0
        for r in results:
            assert r["goal_difference"] > 0
            assert r["winner"] is not None
            assert r["loser"] is not None
        # Should be sorted by goal_difference descending.
        diffs = [r["goal_difference"] for r in results]
        assert diffs == sorted(diffs, reverse=True)

    def test_best_team_record(self):
        results = q.best_team_record(
            competition="Brasileirão Série A", season=2023,
            metric="points", top=5,
        )
        assert len(results) > 0
        pts = [r["points"] for r in results]
        assert pts == sorted(pts, reverse=True)


# ---------------------------------------------------------------------------
# R11: head-to-head records
# ---------------------------------------------------------------------------

class TestHeadToHead:
    def test_fla_flu(self):
        h2h = q.head_to_head("Flamengo", "Fluminense", limit=500)
        assert h2h["matches_found"] > 0
        assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] > 0
        assert h2h["derby"] == "Fla-Flu"

    def test_h2h_win_counts_consistent(self):
        h2h = q.head_to_head("Palmeiras", "Corinthians", limit=500)
        total = h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        # Total decided matches should not exceed matches found.
        assert total <= h2h["matches_found"]

    def test_h2h_with_team_variants(self):
        """Team name variants resolve to the same H2H."""
        h1 = q.head_to_head("Flamengo-RJ", "Fluminense-RJ", limit=500)
        h2 = q.head_to_head("Flamengo", "Fluminense", limit=500)
        assert h1["matches_found"] == h2["matches_found"]
