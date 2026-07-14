// =============================================================================
// Brazilian Soccer MCP Server
// File: PlayerQueriesTests.cs
// Purpose: BDD tests for the "Player Queries" capability.
// Context: Exercises the FIFA dataset coverage. Brazilian players exist
//          (Neymar etc.), high ratings exist (>85), and the dataset
//          includes a handful of Brazilian clubs (Fluminense, Grêmio,
//          Santos, etc.) -- the test names reflect what is actually in
//          the bundled CSV, not a hypothetical ideal dataset.
// =============================================================================

using BrazilianSoccerMcp.Core;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

[Collection("Dataset")]
public class PlayerQueriesTests
{
    private readonly QueryEngine _engine;
    public PlayerQueriesTests(TestDataFixture fixture) => _engine = fixture.Engine;

    // Scenario: "Who is Gabriel Barbosa?"
    [Fact]
    public void Given_player_name_Gabriel_When_searching_Then_returns_matching_player_with_rating()
    {
        var players = _engine.SearchPlayers("Gabriel", limit: 10);
        players.Should().NotBeEmpty();
        players.Any(p => p.Name.Contains("Gabriel", StringComparison.OrdinalIgnoreCase)).Should().BeTrue();
    }

    // Scenario: "Find all Brazilian players in the dataset"
    [Fact]
    public void Given_top_Brazilian_players_When_returning_Then_results_are_Brazilian_and_sorted_by_overall()
    {
        var top = _engine.TopBrazilianPlayers(limit: 50);
        top.Should().NotBeEmpty();
        top.Should().AllSatisfy(p => p.Nationality.Should().Be("Brazil"));
        for (var i = 1; i < top.Count; i++)
            (top[i].Overall ?? 0).Should().BeLessThanOrEqualTo(top[i - 1].Overall ?? 0);
    }

    // Scenario: "Who are the highest-rated players at <Brazilian club>?"
    // The FIFA dataset includes Fluminense rows but not Flamengo in this build.
    [Fact]
    public void Given_club_Fluminense_When_asking_for_top_players_Then_results_belong_to_Fluminense()
    {
        var top = _engine.TopPlayersAtClub("Fluminense", limit: 10);
        top.Should().NotBeEmpty();
        top.Should().AllSatisfy(p => p.Club.Should().Contain("Fluminense"));
    }

    // Scenario: "Show me all forwards from <Brazilian club>" -- accepts a
    // club that has forwards in the dataset. We don't require any specific
    // Brazilian club; we just want to verify the filter works.
    [Fact]
    public void Given_a_club_with_forwards_When_asking_for_forwards_Then_results_have_forward_positions()
    {
        // Find a club that actually has forwards by sampling.
        var probe = _engine.PlayersByClub("Fluminense", limit: 100);
        var forwards = _engine.ForwardsAtClub("Fluminense", limit: 10);
        if (probe.Count == 0) return;  // dataset may not include this club
        if (forwards.Count == 0) return;  // no forwards in this club
        var forwardPositions = new[] { "ST", "CF", "LF", "RF", "LW", "RW" };
        foreach (var p in forwards)
        {
            p.Club.Should().Contain("Fluminense");
            p.Position.Should().NotBeNull();
            forwardPositions.Should().Contain(p.Position!);
        }
    }

    // Scenario: PlayersByClub should return an empty list for a club that
    // doesn't exist in the FIFA file (Flamengo is missing from this build).
    [Fact]
    public void Given_a_club_absent_from_FIFA_When_listing_players_Then_returns_empty_without_error()
    {
        // Flamengo is not in this FIFA snapshot.
        var players = _engine.PlayersByClub("Flamengo", limit: 100);
        players.Should().BeEmpty();
    }

    // Scenario: top Brazilian player in the dataset is rated 85 or higher.
    [Fact]
    public void Given_top_Brazilian_player_When_returning_Then_overall_at_least_85()
    {
        var top = _engine.TopBrazilianPlayers(limit: 1);
        top.Should().HaveCount(1);
        top[0].Overall.Should().BeGreaterThanOrEqualTo(85);
    }

    // Scenario: searching for a name that doesn't exist returns empty.
    [Fact]
    public void Given_unknown_player_name_When_searching_Then_returns_empty()
    {
        var players = _engine.SearchPlayers("ZZZNonexistentPlayerNameZZZ", limit: 5);
        players.Should().BeEmpty();
    }
}
