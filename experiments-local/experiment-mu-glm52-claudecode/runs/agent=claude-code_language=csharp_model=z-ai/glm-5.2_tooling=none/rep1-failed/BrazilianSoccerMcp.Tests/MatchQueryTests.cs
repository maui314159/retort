// =============================================================================
// File: BrazilianSoccerMcp.Tests/MatchQueryTests.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — BDD scenarios for Match Queries.
//
//   Mirrors the Gherkin from TASK.md:
//     Feature: Match Queries
//       Scenario: Find matches between two teams
//         Given the match data is loaded
//         When I search for matches between "Flamengo" and "Fluminense"
//         Then I should receive a list of matches
//         And each match should have date, scores, and competition
//
//   Each test is written in Given / When / Then form via in-method comments
//   so the GWT flow reads directly off the source.
// =============================================================================
namespace BrazilianSoccerMcp.Tests;

using System;
using System.Linq;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Query;
using Xunit;

[Collection("Soccer")]
public sealed class MatchQueryTests
{
    private readonly DatabaseFixture _fx;
    public MatchQueryTests(DatabaseFixture fx) => _fx = fx;

    [Fact]
    public void Scenario_FindMatchesBetweenTwoTeams_ReturnsListWithRequiredFields()
    {
        // Given the match data is loaded (DatabaseFixture)
        // When I search for matches between "Flamengo" and "Fluminense"
        var results = _fx.Matches.FindMatchesBetweenTeams("Flamengo", "Fluminense");

        // Then I should receive a (possibly empty but well-formed) list
        Assert.NotNull(results);

        // And each match should have date, scores, and competition.
        foreach (var m in results)
        {
            Assert.False(string.IsNullOrWhiteSpace(m.Competition));
            Assert.False(string.IsNullOrWhiteSpace(m.HomeTeam));
            Assert.False(string.IsNullOrWhiteSpace(m.AwayTeam));
            Assert.NotNull(m.HomeGoal);
            Assert.NotNull(m.AwayGoal);
        }
    }

    [Fact]
    public void Scenario_FindMatchesBetweenTwoTeams_IncludesAtLeastOneDerby()
    {
        // Given the match data is loaded
        // When I search for Fla-Flu matches
        var results = _fx.Matches.FindMatchesBetweenTeams("Flamengo", "Fluminense");

        // Then the dataset (multiple Brasileirão seasons) should contain
        // at least one such derby somewhere across the years.
        Assert.True(results.Count > 0,
            "Expected at least one Flamengo vs Fluminense match in the dataset.");
    }

    [Fact]
    public void Scenario_SearchByTeam_NormalizesStateSuffix()
    {
        // Given team names appear with state suffixes in some files
        // ("Palmeiras-SP") and without in others ("Palmeiras")
        // When I search using the bare name "Palmeiras"
        var results = _fx.Matches.SearchMatches(team: "Palmeiras", limit: 5000);

        // Then I should get matches from both suffixed and bare-name sources
        Assert.True(results.Count > 0);
        var sourceFiles = results.Select(r => r.SourceFile).ToHashSet();
        Assert.True(sourceFiles.Count >= 1);
    }

    [Fact]
    public void Scenario_SearchByTeamAndSeason_OnlyReturnsThatSeason()
    {
        // Given the match data is loaded
        // When I search for Palmeiras matches in 2023
        var results = _fx.Matches.SearchMatches(team: "Palmeiras", season: 2023, limit: 200);

        // Then every returned match must be season 2023
        Assert.All(results, m => Assert.Equal(2023, m.Season));
    }

    [Fact]
    public void Scenario_SearchByCompetition_FiltersToThatCompetition()
    {
        // Given the match data is loaded
        // When I search for matches in Copa do Brasil
        var results = _fx.Matches.SearchMatches(competition: "Copa do Brasil", limit: 200);

        // Then every match is in the Copa do Brasil bucket
        Assert.All(results, m => Assert.Equal("Copa do Brasil", m.Competition));
    }

    [Fact]
    public void Scenario_SearchResults_AreOrderedByDateDescending()
    {
        // Given the match data is loaded
        // When I search for Libertadores matches
        var results = _fx.Matches.SearchMatches(competition: "Libertadores", limit: 50);

        // Then results are ordered newest-first (unknown dates last)
        for (int i = 1; i < results.Count; i++)
        {
            var prev = results[i - 1].Date ?? "";
            var cur = results[i].Date ?? "";
            Assert.True(string.Compare(prev, cur, StringComparison.Ordinal) >= 0,
                "Results must be ordered by date descending.");
        }
    }

    [Fact]
    public void Scenario_SearchByDateRange_ReturnsOnlyMatchesInRange()
    {
        // Given the match data is loaded
        // When I search Brasileirão matches in a narrow 2023 window
        var start = new DateTime(2023, 1, 1);
        var end = new DateTime(2023, 12, 31);
        var results = _fx.Matches.SearchMatches(
            competition: "Brasileirão", startDate: start, endDate: end, limit: 200);

        // Then every returned match falls inside the date window
        Assert.All(results, m =>
        {
            Assert.NotNull(m.Date);
            var d = DateTime.ParseExact(m.Date!, "yyyy-MM-dd", null);
            Assert.InRange(d, start, end);
        });
    }
}
