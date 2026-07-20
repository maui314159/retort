using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Competition Queries
/// Standings calculated from match results, for both source eras of the
/// Brasileirão (2003 from the historical file, 2019 from the modern file).
/// </summary>
public class StandingsFeatureTests
{
    private readonly TeamAnalyticsService _analytics =
        new(TestData.Graph, new MatchQueryService(TestData.Graph));

    [Fact]
    public void Given_MatchDataLoaded_When_Requesting2019Brasileirao_Then_FlamengoIsChampionWith90Points()
    {
        // Given / When
        var table = _analytics.GetStandings(2019);

        // Then: exactly reproduces the specification's expected answer
        Assert.Equal(20, table.Count);
        var champion = table[0];
        Assert.Equal(1, champion.Position);
        Assert.StartsWith("Flamengo", champion.Team);
        Assert.Equal(90, champion.Points);
        Assert.Equal(28, champion.Wins);
        Assert.Equal(6, champion.Draws);
        Assert.Equal(4, champion.Losses);
        // Every club played all 38 rounds
        Assert.All(table, row => Assert.Equal(38, row.Played));
        // And positions are sequential
        Assert.Equal(Enumerable.Range(1, 20), table.Select(r => r.Position));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_Requesting2003Brasileirao_Then_CruzeiroIsChampion()
    {
        // Given (2003 comes from the historical novo_campeonato file)

        // When
        var table = _analytics.GetStandings(2003);

        // Then: 24-team season, Cruzeiro's 100-point campaign
        Assert.Equal(24, table.Count);
        Assert.Equal("Cruzeiro", table[0].Team);
        Assert.Equal(100, table[0].Points);
    }

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingStandings_Then_PointsEqualThreePerWinPlusDraws()
    {
        // Given / When
        var table = _analytics.GetStandings(2021);

        // Then
        Assert.All(table, row => Assert.Equal(row.Wins * 3 + row.Draws, row.Points));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingRelegationZone2020_Then_BottomFourAreConsistent()
    {
        // Given / When
        var table = _analytics.GetStandings(2020);
        var bottomFour = table.TakeLast(4).ToList();

        // Then: the relegation zone is the four lowest-ranked teams, points non-increasing
        Assert.Equal(20, table.Count);
        Assert.Equal(new[] { 17, 18, 19, 20 }, bottomFour.Select(r => r.Position));
        Assert.All(bottomFour, row => Assert.True(row.Points <= table[15].Points));
    }

    [Fact]
    public void Given_MatchDataLoaded_When_RequestingMostProductiveAttack2023_Then_ItComesFromStandingsGoalsFor()
    {
        // Given / When ("Which team scored the most goals in Serie A 2023?")
        var table = _analytics.GetStandings(2023, "Serie A");
        var bestAttack = table.MaxBy(r => r.GoalsFor);

        // Then
        Assert.NotNull(bestAttack);
        Assert.True(bestAttack!.GoalsFor > 50, $"expected a 50+ goal attack, got {bestAttack.GoalsFor}");
        Assert.All(table, row => Assert.True(row.GoalsFor <= bestAttack.GoalsFor));
    }
}
