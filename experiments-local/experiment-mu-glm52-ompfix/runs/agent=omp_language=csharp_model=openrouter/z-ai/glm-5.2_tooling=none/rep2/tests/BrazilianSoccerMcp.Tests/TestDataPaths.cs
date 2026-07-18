// ============================================================================
// BrazilianSoccerMcp.Tests - TestDataPaths.cs
//
// Context block:
//   Centralizes locating the repo's data/kaggle directory for the test suite.
//   Tests pass this directory to SoccerDataStore so the loaders are exercised
//   against the real CSV files (BDD "Given the match data is loaded").
// ============================================================================

namespace BrazilianSoccerMcp.Tests;

internal static class TestDataPaths
{
    /// <summary>Resolves the repo's data/kaggle directory from the test bin path.</summary>
    public static string KaggleDir()
    {
        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 8 && !string.IsNullOrEmpty(dir); i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate) &&
                File.Exists(Path.Combine(candidate, "Brasileirao_Matches.csv")))
                return candidate;
            dir = Path.GetDirectoryName(dir) ?? "";
        }
        throw new DirectoryNotFoundException(
            "Could not locate data/kaggle from " + AppContext.BaseDirectory);
    }
}
