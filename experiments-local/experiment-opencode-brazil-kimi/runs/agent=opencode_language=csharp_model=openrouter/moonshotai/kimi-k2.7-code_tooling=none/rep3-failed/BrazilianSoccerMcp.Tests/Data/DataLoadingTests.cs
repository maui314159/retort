// <copyright file="DataLoadingTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - BDD: all CSV files must be loadable and queryable.
// </copyright>
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Tests.Fixtures;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Data;

[Collection("Data")]
public class DataLoadingTests
{
    private readonly DataFixture _fixture;

    public DataLoadingTests(DataFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public void GivenAllMatchCsvs_WhenLoaded_ThenAtLeastTwentyThousandMatchesExist()
    {
        _fixture.Context.Matches.Count.Should().BeGreaterThan(20000);
    }

    [Fact]
    public void GivenFifaCsv_WhenLoaded_ThenManyPlayersExist()
    {
        _fixture.Context.Players.Count.Should().BeGreaterThan(18000);
    }

    [Fact]
    public void GivenLoadedData_WhenQueried_BrasileiraoMatchesExist()
    {
        var brasileirao = _fixture.Context.Matches
            .Where(m => m.Competition.Equals("Brasileirão", StringComparison.OrdinalIgnoreCase));

        brasileirao.Should().NotBeEmpty();
        brasileirao.Should().Contain(m => m.Season == 2023);
    }

    [Fact]
    public void GivenLoadedData_WhenQueried_CopaDoBrasilAndLibertadoresMatchesExist()
    {
        _fixture.Context.Matches.Should().Contain(m =>
            m.Competition.Equals("Copa do Brasil", StringComparison.OrdinalIgnoreCase));
        _fixture.Context.Matches.Should().Contain(m =>
            m.Competition.Equals("Copa Libertadores", StringComparison.OrdinalIgnoreCase));
    }
}
