import pytest
import pandas as pd
from brazilian_soccer_mcp import (
    normalize_team_name,
    search_matches,
    get_team_stats,
    get_head_to_head,
    search_players,
    get_competition_standings,
    df_matches,
    df_fifa
)


class TestNormalizeTeamName:
    def test_basic_normalization(self):
        assert normalize_team_name("Palmeiras-SP") == "palmeiras"
        assert normalize_team_name("Flamengo-RJ") == "flamengo"
        assert normalize_team_name(" Sport Club Corinthians Paulista ") == "sport club corinthians paulista"
        assert normalize_team_name("São Paulo") == "são paulo"
        assert normalize_team_name("Grêmio") == "grêmio"

    def test_missing_or_invalid(self):
        assert normalize_team_name(None) == ""
        assert normalize_team_name("") == ""
        assert normalize_team_name(pd.NA) == ""


class TestSearchMatches:
    def test_search_by_team(self):
        result = search_matches(team="Flamengo", limit=5)
        assert "Flamengo" in result
        assert "No matches found" not in result

    def test_search_by_competition(self):
        result = search_matches(competition="Copa do Brasil", limit=5)
        assert "Copa do Brasil" in result

    def test_search_by_season(self):
        result = search_matches(season=2023, limit=5)
        assert "2023" in result

    def test_combined_search(self):
        result = search_matches(team="Palmeiras", competition="Brasileirão", season=2022, limit=5)
        assert "Palmeiras" in result


class TestGetTeamStats:
    def test_basic_stats(self):
        result = get_team_stats(team="Flamengo")
        assert "Statistics for Flamengo" in result
        assert "Matches:" in result
        assert "Wins:" in result
        assert "Win Rate:" in result

    def test_filtered_stats(self):
        result = get_team_stats(team="Palmeiras", season=2022)
        assert "Statistics for Palmeiras" in result
        assert "Matches:" in result


class TestGetHeadToHead:
    def test_h2h_basic(self):
        result = get_head_to_head(team1="Flamengo", team2="Corinthians", limit=5)
        assert "Head-to-Head: Flamengo vs Corinthians" in result
        assert "Total Matches:" in result
        assert "wins:" in result
        assert "Recent Matches:" in result

    def test_h2h_filtered(self):
        result = get_head_to_head(team1="Palmeiras", team2="Santos", competition="Brasileirão")
        assert "Head-to-Head: Palmeiras vs Santos" in result


class TestSearchPlayers:
    def test_search_by_name(self):
        result = search_players(name="Neymar", limit=5)
        assert "Neymar" in result
        assert "Overall:" in result

    def test_search_by_nationality(self):
        result = search_players(nationality="Brazil", limit=5)
        assert "Brazil" in result

    def test_search_by_club(self):
        result = search_players(club="Santos", limit=5)
        assert "Santos" in result

    def test_search_by_min_overall(self):
        result = search_players(min_overall=90, limit=5)
        assert "Overall: 9" in result

    def test_combined_search(self):
        result = search_players(nationality="Brazil", min_overall=85, limit=5)
        assert "Brazil" in result


class TestGetCompetitionStandings:
    def test_standings_basic(self):
        result = get_competition_standings(competition="Brasileirão", season=2019)
        assert "Standings for Brasileirão (2019)" in result
        assert "Pos" in result
        assert "Team" in result
        assert "Pts" in result

    def test_standings_libertadores(self):
        result = get_competition_standings(competition="Copa Libertadores", season=2022)
        assert "Standings for Copa Libertadores (2022)" in result

    def test_standings_not_found(self):
        result = get_competition_standings(competition="Premier League", season=2023)
        assert "No match data found" in result


class TestDataIntegrity:
    def test_matches_loaded(self):
        assert len(df_matches) > 20000

    def test_fifa_loaded(self):
        assert len(df_fifa) > 15000

    def test_matches_have_required_columns(self):
        required_cols = ['competition', 'season', 'date', 'home_team', 'away_team', 'home_goal', 'away_goal']
        for col in required_cols:
            assert col in df_matches.columns

    def test_fifa_has_required_columns(self):
        required_cols = ['Name', 'Overall', 'Club', 'Nationality', 'Position']
        for col in required_cols:
            assert col in df_fifa.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
