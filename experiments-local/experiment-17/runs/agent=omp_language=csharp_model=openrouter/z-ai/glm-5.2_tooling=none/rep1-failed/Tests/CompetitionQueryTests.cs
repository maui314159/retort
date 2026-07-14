// ============================================================================
// File: Tests/CompetitionQueryTests.cs
// ----------------------------------------------------------------------------
// Context: BDD tests for the "Competition Queries" category (CompetitionTools):
// standings, champion, relegated teams.
//
// Feature: Competition Queries
//   Scenario: Who won the 2019 Brasileirão?
//     Given the match data is loaded
//     When I request the champion of Brasileirão 2019
//     Then I should receive Flamengo (the real-world champion)
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

[Collection("Store")]
public class CompetitionQueryTests
{
    private readonly CompetitionTools _tools;

    public CompetitionQueryTests(StoreFixture fixture)
        => _tools = new CompetitionTools(fixture.Store);

    // Given the match data is loaded
    // When I request the champion of Brasileirão 2019
    // Then I should receive Flamengo
    [Fact]
    public void Champion_Brasileirao_2019_is_Flamengo()
    {
        var result = _tools.Champion("Brasileirão", 2019);

        Assert.Contains("Flamengo", result);
        Assert.Contains("champion", result.ToLowerInvariant());
    }

    // Scenario: 2019 Brasileirão standings are calculated from matches
    //   Given the match data is loaded
    //   When I request the 2019 Brasileirão standings
    //   Then Flamengo is top (champion) and the table has 20 teams
    [Fact]
    public void Standings_Brasileirao_2019_has_Flamengo_on_top()
    {
        var result = _tools.Standings("Brasileirão", 2019);

        Assert.Contains("Standings", result);
        // First ranked line is the champion.
        var firstRanked = result.Split('\n').First(l => l.TrimStart().StartsWith("1."));
        Assert.Contains("Flamengo", firstRanked);
        Assert.Contains("Champion", firstRanked);
    }

    // Scenario: Relegated teams from a Brasileirão season
    //   Given the match data is loaded
    //   When I request relegated teams for Brasileirão 2019
    //   Then I receive four teams marked as relegated
    [Fact]
    public void RelegatedTeams_returns_four_teams()
    {
        var result = _tools.RelegatedTeams("Brasileirão", 2019);

        Assert.Contains("Relegated", result);
        var teamLines = result.Split('\n').Where(l => l.TrimStart().StartsWith("- ")).ToList();
        Assert.Equal(4, teamLines.Count);
    }

    // Standings for a season only present in the historical file (pre-2012).
    [Fact]
    public void Standings_historical_season_2003_resolves()
    {
        var result = _tools.Standings("Brasileirão", 2003);
        Assert.Contains("Standings", result);
        Assert.True(result.Split('\n').Length >= 20, "2003 had many Serie A teams.");
    }
}
