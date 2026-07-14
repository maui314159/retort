// ============================================================================
// File: Tests/TeamQueryTests.cs
// ----------------------------------------------------------------------------
// Context: BDD tests for the "Team Queries" category (TeamTools).
//
// Feature: Team Queries
//   Scenario: Get team statistics
//     Given the match data is loaded
//     When I request statistics for "Palmeiras" in season "2023"
//     Then I should receive wins, losses, draws, and goals
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

[Collection("Store")]
public class TeamQueryTests
{
    private readonly SoccerDataStore _store;
    private readonly TeamTools _tools;

    public TeamQueryTests(StoreFixture fixture)
    {
        _store = fixture.Store;
        _tools = new TeamTools(_store);
    }

    // When I request statistics for "Palmeiras" in season "2022"
    // Then I should receive wins, losses, draws, and goals
    [Fact]
    public void TeamStats_Palmeiras_2022_returns_full_record()
    {
        var result = _tools.TeamStats("Palmeiras", competition: "Brasileirão", season: 2022);

        Assert.Contains("Matches:", result);
        Assert.Contains("Wins:", result);
        Assert.Contains("Draws:", result);
        Assert.Contains("Losses:", result);
        Assert.Contains("Goals For:", result);
        Assert.Contains("Goals Against:", result);
        Assert.Contains("Win rate:", result);
    }

    // Scenario: Corinthians home record in 2022
    //   Given the match data is loaded
    //   When I request Corinthians home record for 2022 Brasileirão
    //   Then the match count is positive and win rate is present
    [Fact]
    public void TeamStats_Corinthians_home_2022_returns_home_record()
    {
        var result = _tools.TeamStats("Corinthians", competition: "Brasileirão", season: 2022, venue: "home");

        Assert.Contains("home record", result);
        Assert.Contains("Matches:", result);
        // Parse the match count to assert it is a real season (>0).
        var matchLine = result.Split('\n').First(l => l.Contains("Matches:"));
        var number = int.Parse(matchLine.Split(':')[1].Trim());
        Assert.True(number > 0, "Corinthians should have home matches in 2022.");
    }

    // Scenario: Which team scored the most goals in Serie A 2023
    //   Given the match data is loaded
    //   When I request the top scoring team for Brasileirão 2023
    //   Then I get a ranked list of teams with goal totals
    [Fact]
    public void TopScoringTeam_Brasileirao_2022_returns_ranking()
    {
        var result = _tools.TopScoringTeam("Brasileirão", 2022, top: 5);

        Assert.Contains("Top scoring teams", result);
        Assert.Contains("goals", result);
        var ranked = result.Split('\n').Where(l => l.TrimStart().StartsWith("1.")).ToList();
        Assert.Single(ranked); // a #1 entry
    }

    // Scenario: Compare Palmeiras and Santos head-to-head via team records.
    [Fact]
    public void RecordForTeam_aggregates_win_draw_loss_correctly()
    {
        var matches = _store.MatchesForTeamFiltered("Santos", competition: "Brasileirão", season: 2022).ToList();
        var rec = _store.RecordForTeam("Santos", matches);

        Assert.True(rec.Matches > 0);
        Assert.Equal(rec.Matches, rec.Wins + rec.Draws + rec.Losses);
        Assert.True(rec.GoalsFor >= rec.Wins); // at least one goal per win
    }
}
