// <copyright file="DataFixture.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Shared test fixture that loads CSV data once.
// </copyright>
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Services;

namespace BrazilianSoccerMcp.Tests.Fixtures;

/// <summary>
/// Shared in-memory data context used by the test suite.
/// </summary>
public sealed class DataFixture : IDisposable
{
    public SoccerDataContext Context { get; }
    public SoccerQueryService QueryService { get; }

    public DataFixture()
    {
        var dataDirectory = ResolveDataDirectory();
        var loader = new CsvDataLoader(dataDirectory);
        Context = new SoccerDataContext(loader);
        QueryService = new SoccerQueryService(Context);

        // Force load once, so that tests can measure real query performance.
        _ = Context.Matches.Count;
        _ = Context.Players.Count;
    }

    public void Dispose()
    {
        // No disposable resources to release.
    }

    private static string ResolveDataDirectory()
    {
        // Walk up from the test assembly location until we find data/kaggle.
        var current = AppContext.BaseDirectory;
        for (var i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(current, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;

            var parent = Directory.GetParent(current);
            if (parent == null)
                break;
            current = parent.FullName;
        }

        // Fallback to current working directory.
        return Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
    }
}

[CollectionDefinition("Data")]
public class DataCollection : ICollectionFixture<DataFixture>
{
}
