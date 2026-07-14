// =============================================================================
// Brazilian Soccer MCP Server
// File: MatchQueriesTests.cs
// Purpose: BDD tests for the "Match Queries" capability described in
//          brazilian-soccer-mcp-guide.md / TASK.md.
// Context: Each test names the Gherkin scenario in its display name. The
//          tests run against the real bundled dataset so failures point
//          to actual data quality issues, not just logic bugs.
// =============================================================================

using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Models;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

[Collection("Dataset")]
public class MatchQueriesTests
{
    private readonly QueryEngine _engine;
    public MatchQueriesTests(TestDataFixture fixture) => _engine = fixture.Engine;

    // Scenario: Find matches between two teams
    [Fact]
    public void Given_Flamengo_and_Fluminense_When_searching_head_to_head_Then_returns_matches_with_date_score_competition()
    {
        var result = _engine.HeadToHead("Flamengo", "Fluminense");

        result.Matches.Should().NotBeEmpty();
        foreach (var m in result.Matches)
        {
            m.Date.Should().NotBe(default);
            (m.HomeTeam.Contains("Flamengo", StringComparison.OrdinalIgnoreCase) ||
             m.AwayTeam.Contains("Flamengo", StringComparison.OrdinalIgnoreCase)).Should().BeTrue();
            (m.HomeTeam.Contains("Fluminense", StringComparison.OrdinalIgnoreCase) ||
             m.AwayTeam.Contains("Fluminense", StringComparison.OrdinalIgnoreCase)).Should().BeTrue();
        }
    }

    // Scenario: Team name variation handling -- "Flamengo" must match "Flamengo-RJ"
    [Fact]
    public void Given_team_name_with_state_suffix_When_searching_Then_matches_also_find_unsuffixed_name()
    {
        var bySuffix = _engine.FindMatchesByTeam("Flamengo-RJ");
        var byBare = _engine.FindMatchesByTeam("Flamengo");
        bySuffix.Count.Should().BeGreaterThan(0);
        byBare.Count.Should().BeGreaterThan(0);
        // The two queries should return the same set.
        bySuffix.Count.Should().Be(byBare.Count);
    }

    // Scenario: "What matches did Palmeiras play in 2023?"
    [Fact]
    public void Given_Palmeiras_and_season_2023_When_filtering_by_season_Then_only_2023_matches_returned()
    {
        var matches = _engine.FindMatchesByTeam("Palmeiras", season: 2023);
        matches.Should().NotBeEmpty();
        matches.Should().AllSatisfy(m => m.Season.Should().Be(2023));
    }

    // Scenario: "When did Flamengo last play Corinthians?"
    [Fact]
    public void Given_Flamengo_and_Corinthians_When_asking_for_last_match_Then_returns_most_recent()
    {
        var last = _engine.LastMatchBetween("Flamengo", "Corinthians");
        last.Should().NotBeNull();
        last!.Date.Should().NotBe(default);

        // The last match in the list returned by FindHeadToHead should be
        // the same match.
        var all = _engine.HeadToHead("Flamengo", "Corinthians");
        all.Matches.First().Should().BeEquivalentTo(last);
    }

    // Scenario: "Find all Copa do Brasil finals" -- the bundled dataset
    // labels rounds 1..8 rather than naming them "final". The latest
    // round (8) is the final stage of the cup, so we assert it exists
    // and contains at least one match.
    [Fact]
    public void Given_Copa_do_Brasil_When_searching_for_final_round_Then_round_8_exists_with_matches()
    {
        var cup = _engine.FindMatchesByDate(null, null, Competition.CopaDoBrasil, limit: 50_000);
        var finals = cup
            .Where(m => m.Round is not null && m.Round.Trim('"') == "8")
            .ToList();
        finals.Should().NotBeEmpty("the Copa do Brasil dataset should include final-round matches (round 8)");
    }
    // Scenario: When a queried team does not exist, return empty (no exceptions).
    [Fact]
    public void Given_unknown_team_When_searching_Then_returns_empty_result_without_throwing()
    {
        var matches = _engine.FindMatchesByTeam("Nonexistent Team XYZ");
        matches.Should().BeEmpty();
    }
}
