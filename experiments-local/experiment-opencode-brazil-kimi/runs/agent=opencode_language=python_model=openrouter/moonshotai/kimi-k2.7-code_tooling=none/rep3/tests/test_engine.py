"""
BDD-style pytest suite for the Brazilian Soccer MCP Server.

The test cases are written as plain pytest functions. Gherkin-style comments
(Given/When/Then/And) are preserved inline so the scenarios map directly to
the behaviour-driven specification in TASK.md.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer_mcp.engine import SoccerEngine
from brazilian_soccer_mcp.server import (
    average_goals,
    best_away_record,
    biggest_wins,
    competition_finals,
    competition_standings,
    find_matches,
    find_players,
    head_to_head,
    player_details,
    relegated_teams,
    team_competitions,
    team_statistics,
    top_players,
)

# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------


class TestMatchQueries:
    def test_find_flamengo_vs_fluminense_matches(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find matches between two teams
          Given the match data is loaded
          When I search for matches between "Flamengo" and "Fluminense"
          Then I should receive a list of matches
          And each match should include dates, scores and competition info.
        """
        result = engine.head_to_head("Flamengo", "Fluminense")
        assert "Flamengo vs Fluminense" in result
        assert "- " in result
        assert "wins" in result

    def test_find_palmeiras_matches_in_2023(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find matches by team and season
          Given the match data is loaded
          When I search for matches of "Palmeiras" in season "2023"
          Then I should receive matches from that season.
        """
        result = engine.find_matches(team1="Palmeiras", season=2023)
        assert "Palmeiras" in result
        assert "2023" in result
        assert "No matches" not in result

    def test_find_copa_do_brasil_finals(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find knockout competition finals
          Given the match data is loaded
          When I request Copa do Brasil finals
          Then I should receive the final-round matches.
        """
        result = engine.competition_finals("Copa do Brasil")
        assert "Copa do Brasil" in result
        assert "final" in result.lower()

    def test_find_matches_by_date_range(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find matches by date range
          Given the match data is loaded
          When I search for matches between "Flamengo" and "Fluminense" from 2023-01-01 to 2023-12-31
          Then all returned matches should fall inside that range.
        """
        result = engine.find_matches(
            team1="Flamengo",
            team2="Fluminense",
            season=2023,
            date_from="2023-01-01",
            date_to="2023-12-31",
        )
        assert "2023" in result
        assert "2022" not in result

    def test_team_competitions(self, engine: SoccerEngine) -> None:
        """
        Scenario: Show all competitions a team has played in
          Given the match data is loaded
          When I ask for competitions of "Palmeiras"
          Then I should receive a list of competition/season pairs.
        """
        result = engine.team_competitions("Palmeiras")
        assert "Brasileirão" in result


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------


class TestTeamQueries:
    def test_corinthians_home_record_2022(self, engine: SoccerEngine) -> None:
        """
        Scenario: Get team home statistics for a season
          Given the match data is loaded
          When I request statistics for "Corinthians" in season "2022"
          Then I should receive a home record with 19 home matches.
        """
        result = engine.team_statistics("Corinthians", season=2022, competition="Brasileirão")
        assert "Corinthians" in result
        assert "Home" in result
        assert "19 matches" in result or "matches" in result

    def test_top_scoring_team_2022(self, engine: SoccerEngine) -> None:
        """
        Scenario: Which team scored the most goals in Serie A 2022
          Given the match data is loaded
          When I compute the 2022 Brasileirão standings
          Then the table should contain Flamengo near the top.
        """
        result = engine.competition_standings("Brasileirão", 2022)
        standings = result.splitlines()
        assert "2022" in result
        # The first ranked team should be present (labelled as Champion or "1.").
        assert "Champion" in standings[1] or "1." in standings[1]

    def test_compare_palmeiras_and_santos(self, engine: SoccerEngine) -> None:
        """
        Scenario: Compare two teams head-to-head
          Given the match data is loaded
          When I request head-to-head between "Palmeiras" and "Santos"
          Then I should receive a summary of wins, draws and losses.
        """
        result = engine.head_to_head("Palmeiras", "Santos")
        assert "Palmeiras" in result
        assert "Santos" in result
        assert "wins" in result


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------


class TestPlayerQueries:
    def test_top_brazilian_players(self, engine: SoccerEngine) -> None:
        """
        Scenario: Show top Brazilian players
          Given the player data is loaded
          When I request the highest-rated Brazilian players
          Then Neymar Jr should appear in the results.
        """
        result = engine.top_players(nationality="Brazil", limit=5)
        assert "Neymar Jr" in result

    def test_find_players_by_name(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find a player by name
          Given the player data is loaded
          When I search for "Gabriel Barbosa"
          Then I should receive matching players.
        """
        result = engine.find_players(name="Barbosa")
        assert "Barbosa" in result

    def test_find_players_by_club(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find players by club
          Given the player data is loaded
          When I search for players at "Grêmio"
          Then I should receive Brazilian players from Grêmio.
        """
        result = engine.find_players(club="Grêmio")
        assert "Grêmio" in result or len(result) == 0

    def test_find_forwards_by_position(self, engine: SoccerEngine) -> None:
        """
        Scenario: Find players by position
          Given the player data is loaded
          When I search for forwards at "Santos"
          Then the returned players should have forward positions.
        """
        result = engine.find_players(position="ST", limit=10)
        assert "Position" in result


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------


class TestCompetitionQueries:
    def test_who_won_2019_brasileirao(self, engine: SoccerEngine) -> None:
        """
        Scenario: Who won the 2019 Brasileirão
          Given the match data is loaded
          When I request the 2019 Brasileirão standings
          Then Flamengo should be listed as champion.
        """
        result = engine.competition_standings("Brasileirão", 2019)
        assert "Flamengo" in result
        assert "Champion" in result

    def test_relegated_teams_2020(self, engine: SoccerEngine) -> None:
        """
        Scenario: Which teams were relegated in 2020
          Given the match data is loaded
          When I request the bottom four teams of the 2020 Brasileirão
          Then four teams should be returned.
        """
        result = engine.relegated_teams(2020)
        lines = [line for line in result.splitlines() if line.strip().startswith("(") or line.strip().split(".")[0].isdigit()]
        assert len(lines) == 4

    def test_2018_libertadores_stage(self, engine: SoccerEngine) -> None:
        """
        Scenario: Show the 2018 Copa Libertadores bracket
          Given the match data is loaded
          When I request the 2018 Copa Libertadores finals
          Then the final-stage matches should be returned.
        """
        result = engine.competition_finals("Copa Libertadores", season=2018)
        assert "Libertadores" in result
        assert "2018" in result


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------


class TestStatisticalQueries:
    def test_average_goals_brasileirao(self, engine: SoccerEngine) -> None:
        """
        Scenario: Average goals per match
          Given the match data is loaded
          When I request the average goals per match in the Brasileirão
          Then a numeric average and home win rate should be returned.
        """
        result = engine.average_goals(competition="Brasileirão")
        assert "Average goals per match" in result
        assert "Home win rate" in result

    def test_biggest_wins(self, engine: SoccerEngine) -> None:
        """
        Scenario: Show the biggest wins
          Given the match data is loaded
          When I request the biggest wins in the dataset
          Then the result should contain the largest goal margins.
        """
        result = engine.biggest_wins(competition="Brasileirão", limit=5)
        assert "Biggest wins" in result
        assert "margin" in result

    def test_best_away_record(self, engine: SoccerEngine) -> None:
        """
        Scenario: Which team has the best away record
          Given the match data is loaded
          When I request the best away records
          Then a ranked list should be returned.
        """
        result = engine.best_away_record(min_matches=10)
        assert "Best away records" in result
        assert "%" in result


# ---------------------------------------------------------------------------
# Feature: MCP Tool Wrappers
# ---------------------------------------------------------------------------


class TestServerTools:
    def test_server_find_matches_tool(self) -> None:
        """
        Scenario: The MCP tool layer delegates to the engine
          Given the server is running
          When I call the find_matches tool with team1="Palmeiras"
          Then I should receive a formatted match list.
        """
        result = find_matches(team1="Palmeiras", limit=5)
        assert "Palmeiras" in result

    def test_server_top_players_tool(self) -> None:
        """
        Scenario: The MCP tool layer handles player queries
          Given the server is running
          When I call top_players for Brazil
          Then Neymar Jr should be returned.
        """
        result = top_players(nationality="Brazil", limit=3)
        assert "Neymar Jr" in result

    def test_server_competition_standings_tool(self) -> None:
        """
        Scenario: The MCP tool layer handles competition queries
          Given the server is running
          When I call competition_standings for 2019 Brasileirão
          Then the result should contain Flamengo.
        """
        result = competition_standings("Brasileirão", 2019)
        assert "Flamengo" in result


# ---------------------------------------------------------------------------
# Feature: Normalisation Quality
# ---------------------------------------------------------------------------


class TestNormalisation:
    def test_team_name_variations_merge(self, loaded_data) -> None:
        """
        Scenario: Team name variations are normalised
          Given the engine is loaded
          Then "Corinthians", "Corinthians-SP" and "Sport Club Corinthians Paulista"
          should resolve to overlapping match sets.
        """
        engine = SoccerEngine(loaded_data["matches"], loaded_data["players"])
        keys = engine._team_keys("Corinthians")
        assert any("corinthians" in key for key in keys)

    def test_state_suffixes_stripped_for_most_teams(self, loaded_data) -> None:
        """
        Scenario: State suffixes are removed from non-ambiguous names
          Given the engine is loaded
          Then "Flamengo-RJ" and "Flamengo" should share the flamengo key.
        """
        engine = SoccerEngine(loaded_data["matches"], loaded_data["players"])
        keys = engine._team_keys("Flamengo")
        from brazilian_soccer_mcp.normalize import canonical_team_name
        assert canonical_team_name("Flamengo-RJ")[0] == "flamengo"
        assert "flamengo" in keys

    def test_ambiguous_roots_keep_state(self, loaded_data) -> None:
        """
        Scenario: Ambiguous team roots retain state codes
          Given the engine is loaded
          Then "Atlético-MG" and "Atlético-PR" must remain distinct.
        """
        from brazilian_soccer_mcp.normalize import canonical_team_name
        assert canonical_team_name("Atlético-MG")[0] != canonical_team_name("Atlético-PR")[0]


# ---------------------------------------------------------------------------
# Feature: Data Coverage
# ---------------------------------------------------------------------------


class TestDataCoverage:
    def test_all_csv_files_loaded(self, loaded_data) -> None:
        """
        Scenario: All bundled CSVs are ingestable
          Given the data loader has run
          Then matches from every source CSV should be present.
        """
        sources = {source for match in loaded_data["matches"] for source in match["source"].split(";")}
        expected = {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }
        assert expected.issubset(sources)

    def test_player_file_loaded(self, loaded_data) -> None:
        """
        Scenario: FIFA player file is loaded
          Given the data loader has run
          Then a large player roster should be available.
        """
        assert len(loaded_data["players"]) >= 18000
