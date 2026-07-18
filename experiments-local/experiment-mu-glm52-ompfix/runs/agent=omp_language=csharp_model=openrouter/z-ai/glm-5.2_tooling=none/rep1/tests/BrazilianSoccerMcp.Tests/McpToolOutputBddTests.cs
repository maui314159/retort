// Brazilian Soccer MCP Server - BDD tests for MCP tool output formatting
//
// Context: These tests verify the MCP tool methods return properly formatted
// strings matching the spec's expected answer formats. They exercise the actual
// tool classes (MatchTools, SoccerTools) that the MCP server exposes, ensuring
// the output an LLM would receive is correct and human-readable.

using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests verifying MCP tool methods return properly formatted
/// responses. Maps to the spec's "Returns properly formatted responses"
/// success criterion and the example answer formats.
/// </summary>
public class McpToolOutputBddTests
{
    private readonly SoccerDataService _data = new();

    private SoccerDataService Data
    {
        get { _data.EnsureLoaded(); return _data; }
    }

    // Scenario: Find matches tool returns formatted output
    //   Given the match data is loaded
    //   When I call FindMatches for "Flamengo"
    //   Then the result should contain date, team names, and scores
    [Fact]
    public void FindMatches_returns_formatted_output_with_dates_and_scores()
    {
        // Given
        var tools = new MatchTools(Data);

        // When
        var result = tools.FindMatches(team: "Flamengo", limit: 5);

        // Then
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Flamengo", result, StringComparison.OrdinalIgnoreCase);
        // Each line should have a date pattern yyyy-MM-dd
        Assert.Matches(@"\d{4}-\d{2}-\d{2}", result);
    }

    // Scenario: Head-to-head tool returns comparison
    //   Given the match data is loaded
    //   When I call CompareTeams for "Flamengo" vs "Fluminense"
    //   Then the result should show wins, draws, and losses for both
    [Fact]
    public void CompareTeams_returns_head_to_head_summary()
    {
        // Given
        var tools = new MatchTools(Data);

        // When
        var result = tools.CompareTeams("Flamengo", "Fluminense");

        // Then
        Assert.Contains("Head-to-head", result);
        Assert.Contains("wins", result);
        Assert.Contains("draws", result);
    }

    // Scenario: Team stats tool returns formatted record
    //   Given the match data is loaded
    //   When I call GetTeamStats for "Corinthians"
    //   Then the result should show matches, wins, draws, losses, goals
    [Fact]
    public void GetTeamStats_returns_formatted_record()
    {
        // Given
        var tools = new MatchTools(Data);

        // When
        var result = tools.GetTeamStats("Corinthians");

        // Then
        Assert.Contains("Matches:", result);
        Assert.Contains("Wins:", result);
        Assert.Contains("Draws:", result);
        Assert.Contains("Losses:", result);
        Assert.Contains("Goals For:", result);
        Assert.Contains("Win rate:", result);
    }

    // Scenario: Standings tool returns ranked table
    //   Given the match data is loaded
    //   When I call GetStandings for Brasileirão 2019
    //   Then the result should show ranked teams with points
    [Fact]
    public void GetStandings_returns_ranked_table()
    {
        // Given
        var tools = new SoccerTools(Data);

        // When
        var result = tools.GetStandings("Brasileirão", 2019);

        // Then
        Assert.Contains("Standings", result);
        Assert.Contains("pts", result);
        Assert.Matches(@"\d+\.", result); // Position numbers
    }

    // Scenario: Search players returns ranked list
    //   Given the FIFA data is loaded
    //   When I call SearchPlayers for Brazilian players
    //   Then the result should show player names and ratings
    [Fact]
    public void SearchPlayers_returns_ranked_list_with_ratings()
    {
        // Given
        var tools = new SoccerTools(Data);

        // When
        var result = tools.SearchPlayers(nationality: "Brazil", limit: 5);

        // Then
        Assert.DoesNotContain("No players found", result);
        Assert.Contains("Overall:", result);
    }

    // Scenario: Get champion returns winner
    //   Given the match data is loaded
    //   When I call GetChampion for Brasileirão 2019
    //   Then the result should name the champion with points
    [Fact]
    public void GetChampion_returns_champion_with_points()
    {
        // Given
        var tools = new SoccerTools(Data);

        // When
        var result = tools.GetChampion("Brasileirão", 2019);

        // Then
        Assert.Contains("Champion:", result);
        Assert.Contains("pts", result);
    }

    // Scenario: List teams returns team names
    //   Given the data is loaded
    //   When I call ListTeams with a filter
    //   Then the result should contain matching team names
    [Fact]
    public void ListTeams_returns_matching_team_names()
    {
        // Given
        var tools = new SoccerTools(Data);

        // When
        var result = tools.ListTeams(filter: "fla");

        // Then
        Assert.Contains("Teams", result);
        Assert.Contains("Flamengo", result, StringComparison.OrdinalIgnoreCase);
    }

    // Scenario: Biggest victories tool returns sorted results
    //   Given the match data is loaded
    //   When I call GetBiggestVictories
    //   Then the result should show matches with margins
    [Fact]
    public void GetBiggestVictories_returns_matches_with_margins()
    {
        // Given
        var tools = new SoccerTools(Data);

        // When
        var result = tools.GetBiggestVictories(limit: 5);

        // Then
        Assert.Contains("Biggest victories", result);
        Assert.Contains("margin:", result);
    }

    // Scenario: Query performance - simple lookup under 2 seconds
    //   Given the match data is loaded
    //   When I time a simple team lookup
    //   Then it should complete in under 2 seconds
    [Fact]
    public void Simple_lookup_responds_under_two_seconds()
    {
        // Given
        var service = Data;

        // When
        var sw = System.Diagnostics.Stopwatch.StartNew();
        _ = service.MatchesForTeam("Flamengo").Count();
        sw.Stop();

        // Then
        Assert.True(sw.ElapsedMilliseconds < 2000, $"Lookup took {sw.ElapsedMilliseconds}ms");
    }

    // Scenario: At least 20 sample questions can be answered
    //   Given all data is loaded
    //   When I exercise representative queries across all 5 categories
    //   Then all should return non-empty, valid results
    [Fact]
    public void At_least_20_sample_questions_can_be_answered()
    {
        // Given
        var matchTools = new MatchTools(Data);
        var soccerTools = new SoccerTools(Data);
        var successCount = 0;

        // When - exercise 20+ representative queries
        // Match queries (6)
        if (!matchTools.FindMatches(team: "Flamengo").Contains("No matches")) successCount++;
        if (!matchTools.FindMatches(team: "Palmeiras", season: 2023).Contains("No matches")) successCount++;
        if (!matchTools.FindMatches(competition: "Copa do Brasil").Contains("No matches")) successCount++;
        if (!matchTools.FindMatches(competition: "Libertadores").Contains("No matches")) successCount++;
        if (!matchTools.CompareTeams("Flamengo", "Fluminense").Contains("No head-to-head")) successCount++;
        if (!matchTools.CompareTeams("Palmeiras", "Santos").Contains("No head-to-head")) successCount++;

        // Team queries (4)
        if (matchTools.GetTeamStats("Corinthians").Contains("Matches:")) successCount++;
        if (matchTools.GetTeamStats("Flamengo", homeOnly: true).Contains("Matches:")) successCount++;
        if (matchTools.GetTeamStats("Palmeiras", season: 2023).Contains("Matches:")) successCount++;
        if (matchTools.GetTeamStats("Santos", awayOnly: true).Contains("Matches:")) successCount++;

        // Player queries (5)
        if (!soccerTools.SearchPlayers(nationality: "Brazil").Contains("No players")) successCount++;
        if (!soccerTools.SearchPlayers(name: "Neymar").Contains("No players")) successCount++;
        if (!soccerTools.SearchPlayers(minOverall: 85).Contains("No players")) successCount++;
        if (!soccerTools.GetClubPlayers("Flamengo").Contains("No players found")) successCount++;
        if (!soccerTools.SearchPlayers(position: "ST").Contains("No players")) successCount++;

        // Competition queries (4)
        if (soccerTools.GetStandings("Brasileirão", 2019).Contains("Standings")) successCount++;
        if (soccerTools.GetChampion("Brasileirão", 2019).Contains("Champion")) successCount++;
        if (soccerTools.GetStandings("Brasileirão", 2023).Contains("Standings")) successCount++;
        if (soccerTools.GetChampion("Brasileirão", 2023).Contains("Champion")) successCount++;

        // Statistical queries (3)
        if (soccerTools.GetAggregateStats(competition: "Brasileirão").Contains("Average goals")) successCount++;
        if (soccerTools.GetBiggestVictories().Contains("Biggest victories")) successCount++;
        if (!soccerTools.ListTeams().Contains("No teams")) successCount++;

        // Then
        Assert.True(successCount >= 20, $"Expected >=20 successful queries, got {successCount}");
    }
}
