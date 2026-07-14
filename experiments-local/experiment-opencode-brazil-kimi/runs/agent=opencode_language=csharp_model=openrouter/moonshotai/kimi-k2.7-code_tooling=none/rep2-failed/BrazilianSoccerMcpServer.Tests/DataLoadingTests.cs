using BrazilianSoccerMcpServer.Data;
using BrazilianSoccerMcpServer.Services;

namespace BrazilianSoccerMcpServer.Tests;

public class DataLoadingTests
{
    private readonly SoccerDataStore _store;
    private readonly SoccerQueryService _service;

    public DataLoadingTests()
    {
        var root = Program.FindDataRoot(Directory.GetCurrentDirectory());
        _store = CsvLoader.LoadFromDirectory(root);
        _service = new SoccerQueryService(_store);
    }

    [Fact]
    public void AllCsvFilesAreLoaded()
    {
        Assert.True(_store.Matches.Count > 0, "Matches should be loaded.");
        Assert.True(_store.Players.Count > 0, "Players should be loaded.");
    }

    [Fact]
    public void BrasileiraoMatchesLoaded()
    {
        var brasileirao = _service.FindMatches(competition: "Brasileirão");
        Assert.True(brasileirao.Count > 0, "Brasileirão matches should exist.");
    }

    [Fact]
    public void CopaDoBrasilMatchesLoaded()
    {
        var copa = _service.FindMatches(competition: "Copa do Brasil");
        Assert.True(copa.Count > 0, "Copa do Brasil matches should exist.");
    }

    [Fact]
    public void LibertadoresMatchesLoaded()
    {
        var lib = _service.FindMatches(competition: "Copa Libertadores");
        Assert.True(lib.Count > 0, "Copa Libertadores matches should exist.");
    }

    [Fact]
    public void FifaPlayersLoaded()
    {
        Assert.True(_store.Players.Count >= 18000, $"Expected >= 18000 players, got {_store.Players.Count}");
    }
}
