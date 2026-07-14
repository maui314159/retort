/*
 * Brazilian Soccer MCP Server - BDD Style Tests
 *
 * xUnit tests written in a Given/When/Then style that verify the core
 * query capabilities against the provided Kaggle datasets.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Queries;

namespace BrazilianSoccerMcp.Tests;

public sealed class DataFixture : IDisposable
{
    public DataRepository Repository { get; }
    public QueryEngine Engine { get; }

    public DataFixture()
    {
        var dataDirectory = ResolveDataDirectory();
        Repository = new DataRepository(dataDirectory);
        Engine = new QueryEngine(Repository);
    }

    public void Dispose() { }

    private static string ResolveDataDirectory()
    {
        var outputData = Path.Combine(AppContext.BaseDirectory, "data", "kaggle");
        if (Directory.Exists(outputData)) return outputData;

        var repoData = Path.Combine(Directory.GetCurrentDirectory(), "..", "data", "kaggle");
        if (Directory.Exists(repoData)) return Path.GetFullPath(repoData);

        throw new DirectoryNotFoundException("Could not locate data/kaggle directory for tests.");
    }
}

public abstract class QueryTestBase : IClassFixture<DataFixture>
{
    protected DataFixture Fixture { get; }
    protected QueryEngine Engine => Fixture.Engine;

    protected QueryTestBase(DataFixture fixture)
    {
        Fixture = fixture;
    }
}
