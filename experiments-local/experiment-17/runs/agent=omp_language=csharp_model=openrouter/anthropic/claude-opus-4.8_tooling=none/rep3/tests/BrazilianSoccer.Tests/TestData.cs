// =============================================================================
// File:    TestData.cs
// Project: BrazilianSoccer.Tests
// Purpose: Shared xUnit collection fixture that loads the full dataset once and
//          exposes a ready SoccerDatabase to every test class, plus a helper to
//          locate the data/kaggle directory from the test bin output.
// Context: Loading ~24k matches + 18k players per test would be wasteful; the
//          [CollectionDefinition] shares one DatabaseFixture across the suite.
//          DataPath walks up from the test assembly looking for data/kaggle so
//          tests run from any working directory.
// =============================================================================

using BrazilianSoccer.Core;

namespace BrazilianSoccer.Tests;

public static class TestPaths
{
    public static string DataDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (Directory.Exists(candidate)) return candidate;
            dir = dir.Parent;
        }
        throw new DirectoryNotFoundException("Could not locate data/kaggle from test output.");
    }
}

public sealed class DatabaseFixture
{
    public SoccerDatabase Db { get; }

    public DatabaseFixture() => Db = SoccerDatabase.Load(TestPaths.DataDir());
}

[CollectionDefinition("database")]
public sealed class DatabaseCollection : ICollectionFixture<DatabaseFixture> { }
