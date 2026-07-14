using BrazilianSoccerMcp.Data;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Shared xUnit collection fixture that loads the real Kaggle CSV datasets
/// once for the whole test run. The data lives under <c>data/kaggle/</c>
/// relative to the test project's output directory.
/// </summary>
public sealed class DataFixture : IDisposable
{
    public DataRepository Repository { get; }

    public DataFixture()
    {
        var dir = ResolveKaggleDir();
        Repository = new DataRepository(dir);
        Repository.Load();
    }

    private static string ResolveKaggleDir()
    {
        var candidates = new[]
        {
            Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle"),
            Path.Combine(Directory.GetCurrentDirectory(), "..", "..", "..", "..", "..", "data", "kaggle"),
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "data", "kaggle"),
        };
        foreach (var c in candidates)
        {
            if (Directory.Exists(c)) return Path.GetFullPath(c);
        }
        throw new DirectoryNotFoundException("Could not locate data/kaggle directory for tests.");
    }

    public void Dispose() { }
}

[CollectionDefinition("DataCollection")]
public sealed class DataCollection : ICollectionFixture<DataFixture> { }
