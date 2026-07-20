// =============================================================================
// File: BrazilianSoccerMcp.Tests/StatisticsTests.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — BDD scenarios for Statistical Analysis.
//
//   Covers: average goals per match (rates sum to 100%),
//   biggest wins (sorted by margin), top scoring teams (sorted desc),
//   and overall data coverage across all 6 CSV files.
// =============================================================================
namespace BrazilianSoccerMcp.Tests;

using System.Linq;
using Xunit;

[Collection("Soccer")]
public sealed class StatisticsTests
{
    private readonly DatabaseFixture _fx;
    public StatisticsTests(DatabaseFixture fx) => _fx = fx;

    [Fact]
    public void Scenario_AverageGoals_Brasileirao_RatesSumToOneHundredPercent()
    {
        // Given the match data is loaded
        // When I compute average goals for the Brasileirão
        var dto = _fx.Stats.GetAverageGoals(competition: "Brasileirão");

        // Then the home-win + away-win + draw rates sum to ~100%
        Assert.True(dto.Matches > 0);
        Assert.True(dto.AverageGoalsPerMatch > 0);
        var total = dto.HomeWinRate + dto.AwayWinRate + dto.DrawRate;
        Assert.InRange(total, 99.5, 100.5);
    }

    [Fact]
    public void Scenario_BiggestWins_SortedByMarginDesc()
    {
        // Given the match data is loaded
        // When I request the 20 biggest victories
        var wins = _fx.Stats.GetBiggestWins(limit: 20);

        // Then the list is sorted by margin descending and each has a winner
        Assert.True(wins.Count > 0);
        for (int i = 1; i < wins.Count; i++)
            Assert.True(wins[i - 1].Margin >= wins[i].Margin);
        Assert.All(wins, w => Assert.True(w.Margin > 0));
    }

    [Fact]
    public void Scenario_TopScoringTeams_Brasileirao2023_SortedDesc()
    {
        // Given the match data is loaded
        // When I ask for top-scoring teams in Brasileirão 2023
        var rows = _fx.Stats.GetTopScoringTeams("Brasileirão", 2023, limit: 10);

        // Then the list is sorted by total goals descending
        Assert.True(rows.Count > 0);
        for (int i = 1; i < rows.Count; i++)
            Assert.True(rows[i - 1].GoalsFor >= rows[i].GoalsFor);
    }

    [Fact]
    public void Scenario_DataCoverage_AllSixCsvFilesLoadableAndQueryable()
    {
        // Given the data directory contains all 6 CSV files
        // When the database is built at fixture construction
        var db = _fx.Database;

        // Then match data spans the expected competition buckets
        Assert.True(db.Matches.Count > 20_000,
            $"Expected >20k matches across files, got {db.Matches.Count}");
        Assert.True(db.Players.Count > 18_000,
            $"Expected >18k players, got {db.Players.Count}");

        var competitions = db.Matches.Select(m => m.Competition).Distinct().ToHashSet();
        Assert.Contains("Brasileirão", competitions);
        Assert.Contains("Copa do Brasil", competitions);
        Assert.Contains("Libertadores", competitions);

        var sources = db.Matches.Select(m => m.SourceFile).Distinct().ToHashSet();
        // Five match source files must all be present.
        Assert.True(sources.Count >= 5,
            $"Expected >=5 match source files, got {sources.Count}");
    }

    [Fact]
    public void Scenario_CrossFileQuery_PlayerAndMatchDataBothUsable()
    {
        // Given player and match data are both loaded
        // When I query Brazilian players (player file) AND Flamengo matches
        var players = _fx.Players.SearchPlayers(nationality: "Brazil", limit: 5);
        var matches = _fx.Matches.SearchMatches(team: "Flamengo", limit: 5);

        // Then both sides return data (cross-file queries work)
        Assert.True(players.Count > 0);
        Assert.True(matches.Count > 0);
    }
}
