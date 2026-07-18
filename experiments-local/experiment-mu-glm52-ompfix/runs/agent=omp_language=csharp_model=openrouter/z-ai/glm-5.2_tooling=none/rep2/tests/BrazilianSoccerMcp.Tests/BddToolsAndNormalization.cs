// ============================================================================
// BrazilianSoccerMcp.Tests - BddToolsAndNormalization.cs
//
// Context block:
//   BDD tests for the MCP tool layer's string output and for the team-name
//   normalizer edge cases listed in TASK.md "Data Quality Notes" (state
//   suffixes, full names, diacritics, parentheticals).
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class BddToolsAndNormalization : IClassFixture<DataFixture>
{
    private readonly DataFixture _f;
    public BddToolsAndNormalization(DataFixture f) => _f = f;

    // --- Normalizer edge cases (TASK.md Data Quality Notes) ---

    [Theory]
    [InlineData("Palmeiras-SP", "palmeiras")]
    [InlineData("Palmeiras", "palmeiras")]
    [InlineData("Flamengo-RJ", "flamengo")]
    [InlineData("São Paulo-SP", "sao paulo")]
    [InlineData("São Caetano", "sao caetano")]
    [InlineData("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista")]
    [InlineData("Sport Club Corinthians Paulista", "corinthians paulista")]
    [InlineData("Arapongas Esporte Clube - PR", "arapongas")]
    [InlineData("Grêmio", "gremio")]
    public void Given_team_label_when_normalized_then_state_suffix_diacritics_and_forms_stripped(
        string raw, string expected)
    {
        Assert.Equal(expected, TeamNameNormalizer.NormalizeTeam(raw));
    }

    [Theory]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("São Paulo-SP", "Sao Paulo")]
    [InlineData("Corinthians-SP", "Corinthians")]
    [InlineData("Grêmio-RS", "Gremio")]
    public void Given_two_team_labels_when_compared_then_suffix_and_diacritics_ignored(
        string a, string b)
    {
        Assert.True(TeamNameNormalizer.TeamMatches(a, b));
    }

    // --- Tool output formatting ---

    [Fact]
    public void Given_tools_when_search_matches_called_then_returns_human_readable_string()
    {
        var result = _f.Tools.SearchMatches(team: "Flamengo", season: 2022, limit: 5);
        Assert.Contains("match(es)", result);
        // Should include a score line
        Assert.Contains("-", result);
    }

    [Fact]
    public void Given_tools_when_team_statistics_called_then_includes_wins_draws_losses()
    {
        var result = _f.Tools.TeamStatistics("Palmeiras", season: 2022, competition: "brasileirao");
        Assert.Contains("Wins:", result);
        Assert.Contains("Draws:", result);
        Assert.Contains("Losses:", result);
        Assert.Contains("Win rate:", result);
    }

    [Fact]
    public void Given_tools_when_head_to_head_called_then_lists_counts()
    {
        var result = _f.Tools.HeadToHead("Flamengo", "Fluminense");
        Assert.Contains("wins:", result);
        Assert.Contains("Draws:", result);
    }

    [Fact]
    public void Given_tools_when_standings_called_then_lists_positions()
    {
        var result = _f.Tools.CompetitionStandings("brasileirao", 2022);
        Assert.Contains("Champion", result);
        // numbered positions
        Assert.Contains("1.", result);
    }

    [Fact]
    public void Given_tools_when_top_players_called_then_includes_overall()
    {
        var result = _f.Tools.TopPlayers(limit: 5, nationality: "Brazil");
        Assert.Contains("Overall:", result);
    }

    [Fact]
    public void Given_tools_when_goals_overview_called_then_includes_average()
    {
        var result = _f.Tools.GoalsOverview("brasileirao");
        Assert.Contains("Average goals per match:", result);
    }

    [Fact]
    public void Given_tools_when_list_competitions_called_then_lists_all_competitions()
    {
        var result = _f.Tools.ListCompetitions();
        Assert.Contains("Brasileirao", result);
        Assert.Contains("Libertadores", result);
        Assert.Contains("Players:", result);
    }

    // Scenario: ParseCompetition is case-insensitive and tolerant
    [Theory]
    [InlineData("brasileirao", Competition.Brasileirao)]
    [InlineData("Brasileirao", Competition.Brasileirao)]
    [InlineData("Copa do Brasil", Competition.CopaDoBrasil)]
    [InlineData("libertadores", Competition.Libertadores)]
    [InlineData("br_football", Competition.BrFootball)]
    [InlineData("historico", Competition.HistoricoBrasileirao)]
    [InlineData("", null)]
    [InlineData("nonexistent", null)]
    public void Given_competition_string_when_parsed_then_matches_expected_enum(
        string? input, Competition? expected)
    {
        Assert.Equal(expected, SoccerTools.ParseCompetition(input));
    }

    [Fact]
    public void Given_unknown_team_when_search_then_returns_no_matches_message()
    {
        var result = _f.Tools.SearchMatches(team: "ThisTeamDoesNotExist12345");
        Assert.Equal("No matches found for the given criteria.", result);
    }

    [Fact]
    public void Given_missing_team_for_stats_then_returns_error_message()
    {
        var result = _f.Tools.TeamStatistics("");
        Assert.Equal("Team name is required.", result);
    }
}
