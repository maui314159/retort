// =============================================================================
// Brazilian Soccer MCP Server
// File: TestDataFixture.cs
// Purpose: Locate the bundled CSV data once per test session and expose it
//          to every BDD test. Walks up the directory tree from the test
//          binary until it finds data/kaggle/.
// Context: xUnit collection fixtures run once for the whole assembly, so
//          loading 30k+ rows of CSV repeatedly per test would be wasteful.
// =============================================================================

using BrazilianSoccerMcp.Core;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// One-time dataset loader shared by every BDD test in this assembly.
/// </summary>
public sealed class TestDataFixture
{
    public QueryEngine Engine { get; }

    public TestDataFixture()
    {
        var root = FindDataRoot();
        var data = Dataset.Load(root);
        Engine = new QueryEngine(data);
    }

    private static string FindDataRoot()
    {
        // Walk up from the binary directory until we find data/kaggle.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (Directory.Exists(candidate))
                return dir.FullName;
            dir = dir.Parent;
        }
        throw new DirectoryNotFoundException(
            "Could not locate data/kaggle. Run tests from the repository root.");
    }
}

[CollectionDefinition("Dataset")]
public sealed class DatasetCollection : ICollectionFixture<TestDataFixture> { }
