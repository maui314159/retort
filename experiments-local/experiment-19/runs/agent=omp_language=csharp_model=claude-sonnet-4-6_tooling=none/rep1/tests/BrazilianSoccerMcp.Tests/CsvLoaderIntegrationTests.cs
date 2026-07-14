using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Integration tests that load the real CSV files.
/// Tests are vacuously passing if the data directory cannot be located.
/// </summary>
public class CsvLoaderIntegrationTests
{
    private static string? FindDataPath()
    {
        var dir = AppDomain.CurrentDomain.BaseDirectory;
        for (int depth = 0; depth < 10; depth++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate)) return candidate;
            var parent = Directory.GetParent(dir)?.FullName;
            if (parent is null) break;
            dir = parent;
        }
        return null;
    }

    [Fact]
    public void LoadBrasileirao_ReturnsMatches()
    {
        var path = FindDataPath();
        if (path is null) return;   // data not available — skip gracefully

        var matches = CsvLoaders.LoadBrasileirao(Path.Combine(path, "Brasileirao_Matches.csv"));
        Assert.True(matches.Count > 1000, $"Expected >1000 matches, got {matches.Count}");
        Assert.All(matches, m => Assert.Equal("Brasileirao", m.Competition));
        Assert.All(matches, m => Assert.NotEmpty(m.HomeTeam));
    }

    [Fact]
    public void LoadCopaDoBrasil_ReturnsMatches()
    {
        var path = FindDataPath();
        if (path is null) return;

        var matches = CsvLoaders.LoadCopaDoBrasil(Path.Combine(path, "Brazilian_Cup_Matches.csv"));
        Assert.True(matches.Count > 100, $"Expected >100 matches, got {matches.Count}");
    }

    [Fact]
    public void LoadLibertadores_ReturnsMatches()
    {
        var path = FindDataPath();
        if (path is null) return;

        var matches = CsvLoaders.LoadLibertadores(Path.Combine(path, "Libertadores_Matches.csv"));
        Assert.True(matches.Count > 100, $"Expected >100 matches, got {matches.Count}");
    }

    [Fact]
    public void LoadBrFootball_ReturnsMatches()
    {
        var path = FindDataPath();
        if (path is null) return;

        var matches = CsvLoaders.LoadBrFootball(Path.Combine(path, "BR-Football-Dataset.csv"));
        Assert.True(matches.Count > 1000, $"Expected >1000 matches, got {matches.Count}");
    }

    [Fact]
    public void LoadHistoricalBrasileirao_ReturnsMatches()
    {
        var path = FindDataPath();
        if (path is null) return;

        var matches = CsvLoaders.LoadHistoricalBrasileirao(
            Path.Combine(path, "novo_campeonato_brasileiro.csv"));
        Assert.True(matches.Count > 1000, $"Expected >1000 matches, got {matches.Count}");
    }

    [Fact]
    public void LoadFifaPlayers_ReturnsPlayers()
    {
        var path = FindDataPath();
        if (path is null) return;

        var players = CsvLoaders.LoadFifaPlayers(Path.Combine(path, "fifa_data.csv"));
        Assert.True(players.Count > 1000, $"Expected >1000 players, got {players.Count}");
        Assert.All(players, p => Assert.NotEmpty(p.Name));
    }

    [Fact]
    public void FullRepository_SearchFlamengo()
    {
        var path = FindDataPath();
        if (path is null) return;

        var repo    = DataRepository.LoadFromCsvs(path);
        var matches = repo.FindMatches(team: "Flamengo").ToList();
        Assert.True(matches.Count > 50, $"Expected >50 Flamengo matches, got {matches.Count}");
    }

    [Fact]
    public void FullRepository_Standings2019()
    {
        var path = FindDataPath();
        if (path is null) return;

        var repo  = DataRepository.LoadFromCsvs(path);
        var table = repo.GetStandings(2019, "Brasileirao");

        Assert.NotEmpty(table);
        Assert.Equal(1, table[0].Rank);
        // 2019 champion was Flamengo
        Assert.Contains("Flamengo", table[0].Team, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void FullRepository_PlayerSearch_Brazil()
    {
        var path = FindDataPath();
        if (path is null) return;

        var repo    = DataRepository.LoadFromCsvs(path);
        var players = repo.FindPlayers(nationality: "Brazil").ToList();

        Assert.True(players.Count > 100, $"Expected >100 Brazilian players, got {players.Count}");
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }
}
