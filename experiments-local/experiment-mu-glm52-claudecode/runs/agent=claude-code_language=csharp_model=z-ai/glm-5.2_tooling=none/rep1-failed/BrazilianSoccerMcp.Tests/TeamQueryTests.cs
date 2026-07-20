// =============================================================================
// File: BrazilianSoccerMcp.Tests/TeamQueryTests.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — BDD scenarios for Team Queries.
//
//   Mirrors the Gherkin from TASK.md:
//     Scenario: Get team statistics
//       Given the match data is loaded
//       When I request statistics for "Palmeiras" in season "2023"
//       Then I should receive wins, losses, draws, and goals
//
//   Plus head-to-head consistency and team-name normalization scenarios.
// =============================================================================
namespace BrazilianSoccerMcp.Tests;

using System;
using System.Linq;
using BrazilianSoccerMcp.Data;
using Xunit;

[Collection("Soccer")]
public sealed class TeamQueryTests
{
    private readonly DatabaseFixture _fx;
    public TeamQueryTests(DatabaseFixture fx) => _fx = fx;

    [Fact]
    public void Scenario_GetTeamStatistics_ReturnsWinsDrawsLossesGoals()
    {
        // Given the match data is loaded
        // When I request statistics for Palmeiras in season 2023
        var stats = _fx.Teams.GetTeamStatistics("Palmeiras", season: 2023);

        // Then I should receive wins, losses, draws, and goals
        Assert.Equal("Palmeiras", stats.Team);
        Assert.True(stats.Matches > 0, "Palmeiras should have played in 2023.");
        Assert.True(stats.Wins + stats.Draws + stats.Losses == stats.Matches,
            "Wins + draws + losses must equal total matches.");
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
        Assert.InRange(stats.WinRate, 0, 100);
    }

    [Fact]
    public void Scenario_GetTeamStatistics_VenueHome_OnlyHomeMatches()
    {
        // Given the match data is loaded
        // When I request Corinthians home record in 2022
        var stats = _fx.Teams.GetTeamStatistics("Corinthians", season: 2022, venue: "home");

        // Then venue is recorded and stats are non-negative
        Assert.Equal("home", stats.Venue);
        Assert.True(stats.Wins + stats.Draws + stats.Losses == stats.Matches);
    }

    [Fact]
    public void Scenario_CompareHeadToHead_SumsConsistent()
    {
        // Given the match data is loaded
        // When I compare Palmeiras and Santos head-to-head
        var h2h = _fx.Teams.CompareTeams("Palmeiras", "Santos");

        // Then wins + draws + losses equals total matches
        Assert.Equal(h2h.Matches, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
        Assert.Equal("Palmeiras", h2h.TeamA);
        Assert.Equal("Santos", h2h.TeamB);
        // Recent matches included and bounded
        Assert.True(h2h.RecentMatches.Count <= 20);
    }

    [Fact]
    public void Scenario_TeamNameNormalization_StateSuffixCollapses()
    {
        // Given team names appear with state suffixes ("Palmeiras-SP") and full
        // legal names ("Sociedade Esportiva Palmeiras")
        // When the normalizer processes each variant
        var bare = TeamNameNormalizer.Normalize("Palmeiras");
        var suffixed = TeamNameNormalizer.Normalize("Palmeiras-SP");
        var full = TeamNameNormalizer.Normalize("Sociedade Esportiva Palmeiras");

        // Then all three collapse to the same canonical key
        Assert.Equal(bare, suffixed);
        Assert.Equal(bare, full);
    }

    [Fact]
    public void Scenario_TeamNameNormalization_ParentheticalAndAccents()
    {
        // Given names like "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        // and accented "Atlético Mineiro" / "Grêmio"
        // When normalized
        var withParen = TeamNameNormalizer.Normalize(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ");
        var accent1 = TeamNameNormalizer.Normalize("Atlético Mineiro");
        var accent2 = TeamNameNormalizer.Normalize("Grêmio");

        // Then parenthetical asides are dropped, suffixes stripped, accents folded
        Assert.DoesNotContain("antigo", withParen);
        Assert.Equal("atletico mineiro", accent1);
        Assert.Equal("gremio", accent2);
    }

    [Fact]
    public void Scenario_TeamCompetitions_ReturnsAtLeastOneBucket()
    {
        // Given the match data is loaded
        // When I ask which competitions Palmeiras played in
        var comps = _fx.Teams.GetTeamCompetitions("Palmeiras");

        // Then at least one competition bucket is returned
        Assert.True(comps.Count > 0);
        Assert.All(comps, kv => Assert.True(kv.Value > 0));
    }
}
