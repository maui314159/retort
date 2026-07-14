"""Tests for the Brazilian Soccer MCP server."""

import re

import pytest

from brazilian_soccer_mcp.knowledge_graph import (
    SoccerKnowledgeGraph,
    display_name,
    get_canonical,
    get_knowledge_graph,
)
from brazilian_soccer_mcp.server import mcp, search_matches


@pytest.fixture(scope="module")
def kg() -> SoccerKnowledgeGraph:
    return get_knowledge_graph()


class TestDataLoading:
    def test_all_csvs_loaded(self, kg: SoccerKnowledgeGraph) -> None:
        assert len(kg.matches) > 0
        assert len(kg.players) > 0
        sources = set(kg.matches["source"].unique())
        expected = {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }
        assert expected.issubset(sources)

    def test_competitions_available(self, kg: SoccerKnowledgeGraph) -> None:
        comps = set(kg.matches["competition"].unique())
        assert "Brasileirão" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps


class TestNormalization:
    def test_canonical_famous_clubs(self) -> None:
        assert get_canonical("Flamengo-RJ") == "flamengo"
        assert get_canonical("Clube de Regatas do Flamengo - RJ") == "flamengo"
        assert get_canonical("Palmeiras-SP") == "palmeiras"
        assert get_canonical("São Paulo - SP") == "sao-paulo"
        assert get_canonical("Athletico Paranaense - PR") == "atletico-pr"

    def test_sub_clubs_are_distinct(self) -> None:
        # Flamengo do Piauí and Fluminense de Feira must not collapse to the big clubs.
        assert get_canonical("Flamengo do Piauí - PI") != "flamengo"
        assert get_canonical("Fluminense de Feira - BA") != "fluminense"

    def test_display_name(self) -> None:
        assert display_name("Flamengo-RJ") == "Flamengo"
        assert display_name("Athletico Paranaense - PR") == "Athletico-PR"


class TestMatchQueries:
    def test_search_matches_by_team_and_season(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.search_matches(team="Palmeiras", season=2023, limit=5)
        assert "Found" in result
        assert "Palmeiras" in result
        assert "Brasileirão" in result
        # Each line should contain a date and a score.
        lines = [line for line in result.splitlines() if line.startswith("-")]
        assert len(lines) > 0
        for line in lines:
            assert re.search(r"\d{4}-\d{2}-\d{2}", line)
            assert re.search(r"\d+-\d+", line)

    def test_search_matches_by_competition(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.search_matches(competition="Copa do Brasil", limit=5)
        assert "Found" in result
        assert "Copa do Brasil" in result

    def test_head_to_head(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_head_to_head("Flamengo", "Fluminense", limit=5)
        assert "Flamengo" in result
        assert "Fluminense" in result
        assert "wins" in result.lower()
        # Record line pattern: e.g. "Flamengo 18 wins, Fluminense 14 wins, 12 draws"
        assert re.search(r"\d+ wins", result)


class TestTeamQueries:
    def test_team_stats(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_team_stats("Corinthians", competition="Brasileirão", season=2022, venue="home")
        assert "Corinthians" in result
        assert "Matches:" in result
        assert "Win rate:" in result
        # A full home season has 19 matches.
        match = re.search(r"Matches: (\d+)", result)
        assert match is not None
        assert int(match.group(1)) == 19

    def test_team_stats_overall(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_team_stats("Flamengo", competition="Brasileirão", season=2019)
        assert "Flamengo" in result
        assert "Wins:" in result


class TestCompetitionQueries:
    def test_standings(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_competition_standings("Brasileirão", season=2019, limit=5)
        assert "Final Standings" in result
        assert "Flamengo" in result
        assert "Champion" in result
        # Expected champion points for 2019.
        assert "90 pts" in result

    def test_top_scoring_teams(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_top_scoring_teams(competition="Brasileirão", season=2023, limit=5)
        assert "goals" in result

    def test_biggest_wins(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_biggest_wins(competition="Brasileirão", season=2019, limit=5)
        assert "Biggest victories" in result or "victories" in result

    def test_average_goals(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.get_average_goals(competition="Brasileirão", season=2019)
        assert "Average goals per match" in result
        assert "Home win rate" in result


class TestPlayerQueries:
    def test_search_players_by_nationality(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.search_players(nationality="Brazil", limit=5)
        assert "Neymar" in result or "Brazil" in result
        assert "Overall:" in result

    def test_search_players_by_name(self, kg: SoccerKnowledgeGraph) -> None:
        result = kg.search_players(name="Neymar")
        assert "Neymar" in result


class TestServerTools:
    def test_server_tool_wrapper(self) -> None:
        # The MCP wrapper should delegate to the knowledge graph.
        result = search_matches(team="Palmeiras", season=2023, limit=5)
        assert "Found" in result
        assert "Palmeiras" in result

    def test_server_lists_tools(self) -> None:
        import asyncio

        tools = asyncio.run(mcp.list_tools())
        names = {tool.name for tool in tools}
        assert "search_matches" in names
        assert "get_head_to_head" in names
        assert "get_team_stats" in names
        assert "search_players" in names
        assert "get_competition_standings" in names
