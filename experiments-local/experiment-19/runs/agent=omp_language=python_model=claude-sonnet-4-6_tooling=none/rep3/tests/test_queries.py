"""
Tests for the Brazilian Soccer MCP server query functions.

Operates against the real CSV data files; verifies correct filtering,
result formatting, and statistics accuracy.
"""

import re
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_loader import DataStore, normalize_team, get_store
import queries as q


# ---------------------------------------------------------------------------
# Shared fixture — load data once for the entire test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def store() -> DataStore:
    return get_store()


# ---------------------------------------------------------------------------
# normalize_team
# ---------------------------------------------------------------------------

class TestNormalizeTeam:
    def test_strips_state_suffix(self):
        assert normalize_team("Palmeiras-SP") == "Palmeiras"

    def test_strips_two_letter_suffix(self):
        assert normalize_team("Flamengo-RJ") == "Flamengo"

    def test_no_suffix_unchanged(self):
        assert normalize_team("Santos") == "Santos"

    def test_strips_space_dash_state(self):
        result = normalize_team("América - MG")
        assert "MG" not in result

    def test_handles_non_string(self):
        result = normalize_team(123)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# DataStore loading
# ---------------------------------------------------------------------------

class TestDataStoreLoading:
    def test_brasileirao_loaded(self, store):
        assert len(store.brasileirao) > 4000

    def test_copa_brasil_loaded(self, store):
        assert len(store.copa_brasil) > 1000

    def test_libertadores_loaded(self, store):
        assert len(store.libertadores) > 1000

    def test_br_football_loaded(self, store):
        assert len(store.br_football) > 5000

    def test_historico_loaded(self, store):
        assert len(store.historico) > 5000

    def test_fifa_loaded(self, store):
        assert len(store.fifa) > 10000

    def test_all_matches_combined(self, store):
        assert len(store.all_matches) > len(store.brasileirao)

    def test_all_matches_has_required_columns(self, store):
        for col in ("date", "home_team", "away_team", "home_goals", "away_goals",
                    "competition", "season"):
            assert col in store.all_matches.columns, f"Missing column: {col}"

    def test_goals_are_integers(self, store):
        assert store.all_matches["home_goals"].dtype.kind == "i"
        assert store.all_matches["away_goals"].dtype.kind == "i"


# ---------------------------------------------------------------------------
# find_matches
# ---------------------------------------------------------------------------

class TestFindMatches:
    def test_find_by_single_team(self, store):
        result = q.find_matches(store, team="Flamengo")
        assert "Flamengo" in result
        assert "matches" in result.lower()

    def test_head_to_head_returns_both_teams(self, store):
        result = q.find_matches(store, team="Flamengo", team2="Fluminense")
        assert "Flamengo" in result
        assert "Fluminense" in result
        assert "Head-to-head" in result

    def test_head_to_head_win_counts(self, store):
        result = q.find_matches(store, team="Palmeiras", team2="Santos")
        assert "wins" in result.lower()
        assert "draws" in result.lower()

    def test_filter_by_competition(self, store):
        result = q.find_matches(store, team="Flamengo", competition="libertadores")
        assert "Libertadores" in result

    def test_filter_by_season(self, store):
        result = q.find_matches(store, team="Palmeiras", season=2023)
        assert "2023" in result

    def test_no_results_returns_informative_message(self, store):
        result = q.find_matches(store, team="NonExistentTeamXYZ999")
        assert "No matches found" in result

    def test_limit_respected(self, store):
        result = q.find_matches(store, team="Flamengo", limit=5)
        # Match lines start with "  20" (ISO date) or "  19"
        match_lines = [l for l in result.split("\n")
                       if l.strip()[:4].isdigit() and "-" in l.strip()[:10]]
        assert len(match_lines) <= 5

    def test_date_filter(self, store):
        result = q.find_matches(store, date_from="2022-01-01", date_to="2022-12-31")
        for line in result.split("\n"):
            stripped = line.strip()
            if re.match(r"\d{4}-\d{2}-\d{2}", stripped):
                assert stripped[:4] == "2022", f"Unexpected date in: {stripped}"


# ---------------------------------------------------------------------------
# get_team_stats
# ---------------------------------------------------------------------------

class TestGetTeamStats:
    def test_returns_wins_draws_losses(self, store):
        result = q.get_team_stats(store, team="Corinthians")
        assert "Wins" in result
        assert "Draws" in result
        assert "Losses" in result

    def test_goals_for_and_against(self, store):
        result = q.get_team_stats(store, team="Flamengo")
        assert "Goals For" in result
        assert "Goals Against" in result

    def test_home_only_flag(self, store):
        result = q.get_team_stats(store, team="Palmeiras", home_only=True)
        assert "home" in result.lower()

    def test_away_only_flag(self, store):
        result = q.get_team_stats(store, team="Santos", away_only=True)
        assert "away" in result.lower()

    def test_season_filter(self, store):
        result = q.get_team_stats(store, team="Palmeiras", season=2022)
        assert "2022" in result

    def test_win_rate_present(self, store):
        result = q.get_team_stats(store, team="Corinthians")
        assert "Win rate" in result

    def test_unknown_team_message(self, store):
        result = q.get_team_stats(store, team="TeamThatDoesNotExist999")
        assert "No data found" in result

    def test_stats_are_consistent(self, store):
        """Wins + Draws + Losses should equal total Matches."""
        result = q.get_team_stats(store, team="Grêmio", season=2018)
        # Output format: one stat per line, e.g. "  Wins: 22"
        parsed: dict[str, int] = {}
        for line in result.split("\n"):
            stripped = line.strip()
            for key in ("Matches", "Wins", "Draws", "Losses"):
                if stripped.startswith(f"{key}:"):
                    try:
                        parsed[key] = int(stripped.split(":", 1)[1].strip())
                    except ValueError:
                        pass
        if "Matches" in parsed and all(k in parsed for k in ("Wins", "Draws", "Losses")):
            assert parsed["Wins"] + parsed["Draws"] + parsed["Losses"] == parsed["Matches"]


# ---------------------------------------------------------------------------
# find_players
# ---------------------------------------------------------------------------

class TestFindPlayers:
    def test_find_by_nationality_brazil(self, store):
        result = q.find_players(store, nationality="Brazil")
        assert "Brazil" in result

    def test_find_by_name(self, store):
        result = q.find_players(store, name="Neymar")
        assert "Neymar" in result

    def test_find_by_club_santos(self, store):
        # Santos is a Brazilian club present in the FIFA dataset
        result = q.find_players(store, club="Santos")
        assert "Santos" in result

    def test_sorted_by_rating(self, store):
        result = q.find_players(store, nationality="Brazil", limit=5)
        lines = [l for l in result.split("\n") if "Overall:" in l]
        ratings = []
        for ln in lines:
            m = re.search(r"Overall:\s*(\d+)", ln)
            if m:
                ratings.append(int(m.group(1)))
        assert ratings == sorted(ratings, reverse=True)

    def test_min_rating_filter(self, store):
        result = q.find_players(store, min_rating=85)
        for ln in result.split("\n"):
            m = re.search(r"Overall:\s*(\d+)", ln)
            if m:
                assert int(m.group(1)) >= 85

    def test_no_match_returns_message(self, store):
        result = q.find_players(store, name="ZZZPlayerDoesNotExist999ZZZ")
        assert "No players found" in result

    def test_position_filter(self, store):
        result = q.find_players(store, position="GK", nationality="Brazil", limit=5)
        assert "GK" in result


# ---------------------------------------------------------------------------
# get_standings
# ---------------------------------------------------------------------------

class TestGetStandings:
    def test_brasileirao_2019(self, store):
        result = q.get_standings(store, season=2019)
        assert "2019" in result
        # Flamengo won 2019 Brasileirao — should appear at top
        lines = result.split("\n")
        flamengo_pos = None
        for line in lines:
            if "Flamengo" in line:
                stripped = line.strip()
                parts = stripped.split()
                if parts and parts[0].isdigit():
                    flamengo_pos = int(parts[0])
                    break
        assert flamengo_pos is not None, "Flamengo not found in 2019 standings"
        assert flamengo_pos <= 3, f"Flamengo should be top 3 in 2019, got {flamengo_pos}"

    def test_standings_has_points(self, store):
        result = q.get_standings(store, season=2018)
        assert "Pts" in result

    def test_standings_unknown_season_returns_message(self, store):
        result = q.get_standings(store, season=1800)
        assert "No match data" in result

    def test_standings_columns_present(self, store):
        result = q.get_standings(store, season=2015)
        assert "W" in result
        assert "D" in result
        assert "L" in result


# ---------------------------------------------------------------------------
# get_biggest_wins
# ---------------------------------------------------------------------------

class TestGetBiggestWins:
    def test_returns_matches(self, store):
        result = q.get_biggest_wins(store, limit=5)
        lines = [l for l in result.split("\n") if l.strip().startswith(("1.", "2.", "3."))]
        assert len(lines) >= 3

    def test_diff_in_output(self, store):
        result = q.get_biggest_wins(store, limit=5)
        assert "diff:" in result

    def test_competition_filter(self, store):
        # "brasileirao" should match "Brasileirão Série A" via accent-insensitive comparison
        result = q.get_biggest_wins(store, competition="brasileirao", limit=5)
        assert "Brasileir" in result or "Serie A" in result

    def test_season_filter(self, store):
        result = q.get_biggest_wins(store, season=2019, limit=5)
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", result)
        for d in dates:
            assert d.startswith("2019")


# ---------------------------------------------------------------------------
# get_competition_stats
# ---------------------------------------------------------------------------

class TestGetCompetitionStats:
    def test_returns_avg_goals(self, store):
        # "brasileirao" → matches "Brasileirão Série A" via accent-insensitive filter
        result = q.get_competition_stats(store, competition="brasileirao")
        assert "Average goals" in result

    def test_home_away_draw_percentages(self, store):
        result = q.get_competition_stats(store)
        assert "Home wins" in result
        assert "Away wins" in result
        assert "Draws" in result

    def test_percentages_sum_to_100(self, store):
        result = q.get_competition_stats(store, competition="Brasileirão Série A", season=2019)
        pcts = re.findall(r"\((\d+\.\d+)%\)", result)
        if len(pcts) >= 3:
            total = sum(float(p) for p in pcts[:3])
            assert abs(total - 100.0) < 0.2, f"Percentages don't sum to 100: {pcts}"


# ---------------------------------------------------------------------------
# get_best_records
# ---------------------------------------------------------------------------

class TestGetBestRecords:
    def test_home_records(self, store):
        result = q.get_best_records(store, record_type="home", min_matches=20)
        assert "Home Records" in result

    def test_away_records(self, store):
        result = q.get_best_records(store, record_type="away", min_matches=20)
        assert "Away Records" in result

    def test_overall_records(self, store):
        result = q.get_best_records(store, record_type="overall", min_matches=50)
        assert "Overall Records" in result

    def test_win_pct_descending(self, store):
        result = q.get_best_records(store, record_type="home", min_matches=50)
        pcts = [float(m) for m in re.findall(r"(\d+\.\d+)%", result)]
        if len(pcts) >= 2:
            assert pcts == sorted(pcts, reverse=True), "Win% should be descending"
