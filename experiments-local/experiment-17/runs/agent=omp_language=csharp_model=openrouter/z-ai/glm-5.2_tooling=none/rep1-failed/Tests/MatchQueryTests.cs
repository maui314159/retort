// ============================================================================
// File: Tests/MatchQueryTests.cs
// ----------------------------------------------------------------------------
// Context: BDD tests for the "Match Queries" category (MatchTools).
//
// Feature: Match Queries
//   Scenario: Find matches between two teams
//     Given the match data is loaded
//     When I search for matches between "Flamengo" and "Fluminense"
//     Then I should receive a list of matches
//     And each match should have date, scores, and competition
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

[Collection("Store")]
public class MatchQueryTests
{
    private readonly SoccerDataStore _store;
    private readonly MatchTools _tools;

    public MatchQueryTests(StoreFixture fixture)
    {
        _store = fixture.Store;
        _tools = new MatchTools(_store);
    }

    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    // Then I should receive a non-empty list
    // And the head-to-head record reports wins for both and draws
    [Fact]
    public void HeadToHead_Flamengo_vs_Fluminense_returns_record_and_matches()
    {
        var result = _tools.HeadToHead("Flamengo", "Fluminense");

        Assert.Contains("Flamengo", result);
        Assert.Contains("Fluminense", result);
        Assert.Contains("wins", result);
        Assert.Contains("draws", result);
        // The Fla-Flu derby must have happened more than a handful of times.
        Assert.Contains("-", result); // a score line
    }
    // When I search for matches Palmeiras played in season 2022
    // Then I should receive matches, each tagged with a competition
    [Fact]
    public void SearchMatches_Palmeiras_2022_returns_matches()
    {
        var result = _tools.SearchMatches(team: "Palmeiras", season: 2022, limit: 10);

        Assert.Contains("Found", result);
        Assert.Contains("Palmeiras", result);
        Assert.Contains("Brasileir", result); // competition label
    }

    // Given the match data is loaded
    // When I search matches in the Copa do Brasil for a season
    // Then results are limited to that competition
    [Fact]
    public void SearchMatches_by_competition_filters_results()
    {
        var result = _tools.SearchMatches(competition: "Copa do Brasil", season: 2021, limit: 10);

        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Copa do Brasil", result);
    }

    // Given the match data is loaded
    // When I ask for the last match between two teams
    // Then I get a single match with a date and score
    [Fact]
    public void LastMatch_returns_most_recent_meeting()
    {
        var result = _tools.LastMatch("Flamengo", "Corinthians");

        Assert.Contains("Last meeting", result);
        Assert.Matches(@"\d{4}-\d{2}-\d{2}", result); // a date
    }

    // Given the match data is loaded
    // When I search by date range
    // Then only matches within the range are returned
    [Fact]
    public void SearchMatches_by_date_range_filters()
    {
        var result = _tools.SearchMatches(
            team: "Flamengo", fromDate: "2023-01-01", toDate: "2023-12-31", limit: 200);

        Assert.DoesNotContain("No matches found", result);
        // Every listed line starts with "- YYYY-MM-DD" within 2023.
        var lines = result.Split('\n').Where(l => l.StartsWith("- ")).ToList();
        Assert.NotEmpty(lines);
        Assert.All(lines, l => Assert.Contains("2023-", l));
    }

    // Cross-file query: Palmeiras appears in multiple competitions.
    [Fact]
    public void TeamCompetitions_spans_multiple_competitions()
    {
        var comps = _store.CompetitionsForTeam("Palmeiras");
        Assert.Contains(comps, c => c.Contains("Brasileir"));
        Assert.True(comps.Count >= 2, "Palmeiras should appear in multiple competitions.");
    }
}
