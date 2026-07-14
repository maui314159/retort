// <copyright file="PerformanceTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD scenarios for query performance.
// </copyright>
using System.Diagnostics;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Services;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Performance;

[Collection("Data")]
public class PerformanceTests
{
    private readonly SoccerQueryService _queryService;

    public PerformanceTests(DataFixture fixture)
    {
        _queryService = fixture.QueryService;
    }

    [Fact]
    public void SimpleLookup_MatchesBetweenTwoTeams_ShouldCompleteWithinTwoSeconds()
    {
        var stopwatch = Stopwatch.StartNew();
        var matches = _queryService.GetHeadToHead("Flamengo", "Corinthians");
        stopwatch.Stop();

        matches.Should().NotBeNull();
        stopwatch.Elapsed.Should().BeLessThan(TimeSpan.FromSeconds(2));
    }

    [Fact]
    public void AggregateQuery_StandingsForASeason_ShouldCompleteWithinFiveSeconds()
    {
        var stopwatch = Stopwatch.StartNew();
        var table = _queryService.GetStandings("Brasileirão", 2019);
        stopwatch.Stop();

        table.Should().NotBeEmpty();
        stopwatch.Elapsed.Should().BeLessThan(TimeSpan.FromSeconds(5));
    }

    [Fact]
    public void AggregateQuery_BiggestWins_ShouldCompleteWithinFiveSeconds()
    {
        var stopwatch = Stopwatch.StartNew();
        var wins = _queryService.GetBiggestWins("Brasileirão", 10);
        stopwatch.Stop();

        wins.Should().NotBeEmpty();
        stopwatch.Elapsed.Should().BeLessThan(TimeSpan.FromSeconds(5));
    }
}
