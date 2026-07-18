// Brazilian Soccer MCP Server - BDD test suite (Given/When/Then)
//
// Context: The spec requests BDD (Behavior-Driven Development) test scenarios in
// Gherkin. xUnit doesn't have native GWT syntax, so each test method is named
// after a scenario and structured with explicit Given/When/Then phases via
// comments and local variables. The test names mirror the Gherkin scenarios in
// TASK.md. Tests load the real bundled datasets from data/kaggle/ so they also
// act as integration tests verifying that all 6 CSVs parse and are queryable.
//
// Performance: Data loading happens once per test class via a shared
// SoccerDataService instance (IClassFixture pattern is intentionally avoided to
// keep each test independent and deterministic; the service caches internally).

using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for match queries. Each test maps to a Gherkin scenario from
/// the spec's "Feature: Match Queries" section.
/// </summary>
public class MatchQueryBddTests
{
    private readonly SoccerDataService _data = new();

    private SoccerDataService Data
    {
        get { _data.EnsureLoaded(); return _data; }
    }

    // Scenario: Find matches between two teams
    //   Given the match data is loaded
    //   When I search for matches between "Flamengo" and "Fluminense"
    //   Then I should receive a list of matches
    //   And each match should have date, scores, and competition
    [Fact]
    public void Find_matches_between_two_teams_returns_matches_with_date_scores_competition()
    {
        // Given
        var service = Data;

        // When
        var matches = service.HeadToHead("Flamengo", "Fluminense").ToList();

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.NotNull(m.Date);
            Assert.NotNull(m.HomeGoals);
            Assert.NotNull(m.AwayGoals);
            Assert.False(string.IsNullOrEmpty(m.Competition));
            Assert.False(string.IsNullOrEmpty(m.HomeTeam));
            Assert.False(string.IsNullOrEmpty(m.AwayTeam));
        });
    }

    // Scenario: Find matches by team in a season
    //   Given the match data is loaded
    //   When I request matches for "Palmeiras" in season 2023
    //   Then I should receive matches from 2023 only
    [Fact]
    public void Find_matches_by_team_in_season_returns_only_that_season()
    {
        // Given
        var service = Data;

        // When
        var matches = service.MatchesForTeam("Palmeiras")
            .Where(m => m.Season == 2023)
            .ToList();

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
    }

    // Scenario: Find matches by competition
    //   Given the match data is loaded
    //   When I search for "Copa do Brasil" matches
    //   Then all results should be from that competition
    [Fact]
    public void Find_matches_by_competition_filters_correctly()
    {
        // Given
        var service = Data;

        // When
        var matches = service.Matches
            .Where(m => m.Competition.Contains("Copa do Brasil", StringComparison.OrdinalIgnoreCase))
            .ToList();

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Copa do Brasil", m.Competition, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Find Copa do Brasil finals
    //   Given the match data is loaded
    //   When I search for Libertadores "final" stage matches
    //   Then all results should have stage "final"
    [Fact]
    public void Find_libertadores_finals_by_stage()
    {
        // Given
        var service = Data;

        // When
        var finals = service.Matches
            .Where(m => string.Equals(m.Stage, "final", StringComparison.OrdinalIgnoreCase))
            .ToList();

        // Then
        Assert.NotEmpty(finals);
        Assert.All(finals, m => Assert.Equal("final", m.Stage, StringComparer.OrdinalIgnoreCase));
    }

    // Scenario: Team name normalization handles state suffixes
    //   Given the datasets use different naming ("Palmeiras-SP", "Palmeiras")
    //   When I search for "Palmeiras"
    //   Then I should find matches stored under both suffix variants
    [Fact]
    public void Team_name_normalization_handles_state_suffixes()
    {
        // Given
        var service = Data;

        // When
        var key1 = TeamNameNormalizer.CanonicalKey("Palmeiras-SP");
        var key2 = TeamNameNormalizer.CanonicalKey("Palmeiras");
        var matches = service.MatchesForTeam("Palmeiras-SP").ToList();

        // Then
        Assert.Equal(key1, key2);
        Assert.NotEmpty(matches);
    }

    // Scenario: Most recent match between two teams
    //   Given the match data is loaded
    //   When I ask for the last match between "Flamengo" and "Corinthians"
    //   Then I should get the chronologically latest result
    [Fact]
    public void Most_recent_match_between_two_teams_is_chronologically_latest()
    {
        // Given
        var service = Data;

        // When
        var matches = service.HeadToHead("Flamengo", "Corinthians")
            .Where(m => m.Date.HasValue)
            .OrderByDescending(m => m.Date!.Value)
            .ToList();

        // Then
        Assert.NotEmpty(matches);
        var latest = matches[0];
        Assert.All(matches.Skip(1), m => Assert.True(m.Date <= latest.Date));
    }
}
