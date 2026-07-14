using BrazilianSoccerCore.Data;
using BrazilianSoccerCore.Queries;
using Xunit;

namespace BrazilianSoccerMcp.Tests.Infrastructure;

/// <summary>
/// Shared fixture that loads all CSV datasets once and exposes the query engines.
/// The data directory is resolved by walking up from the test output path until
/// a "data/kaggle" directory is found.
/// </summary>
public sealed class DataFixture
{
    public DataLoader Loader { get; }
    public MatchQueryEngine Matches { get; }
    public PlayerQueryEngine Players { get; }
    public CompetitionQueryEngine Competitions { get; }
    public StatisticsEngine Stats { get; }

    public DataFixture()
    {
        var dataDir = ResolveDataDir();
        Loader = new DataLoader(dataDir);
        Matches = new MatchQueryEngine(Loader.Matches);
        Players = new PlayerQueryEngine(Loader.Players);
        Competitions = new CompetitionQueryEngine(Loader.Matches);
        Stats = new StatisticsEngine(Loader.Matches);
    }

    private static string ResolveDataDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;
            dir = dir.Parent;
        }
        throw new InvalidOperationException(
            $"Could not locate data/kaggle starting from {AppContext.BaseDirectory}.");
    }
}

/// <summary>xUnit collection fixture wrapper so all tests share one data load.</summary>
[CollectionDefinition("SoccerData")]
public sealed class SoccerDataCollection : ICollectionFixture<DataFixture> { }