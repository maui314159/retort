// =============================================================================
// BrazilianSoccerMcp.Tests - Test Harness
// -----------------------------------------------------------------------------
// Context: Shared setup for the BDD (Given/When/Then) test suite. The Kaggle
// CSV files live in data/kaggle at the repository root; tests locate them by
// walking up from the test bin directory until that folder is found, so the
// suite runs identically from `dotnet test` and any IDE.
// =============================================================================
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

public class TestBase
{
    private static readonly Lazy<SoccerDataRepository> _repo = new(BuildRepo);
    protected static SoccerDataRepository Repo => _repo.Value;
    protected static SoccerTools Tools => new(Repo);

    private static SoccerDataRepository BuildRepo()
    {
        var dir = LocateDataDir();
        return new SoccerDataRepository(dir);
    }

    private static string LocateDataDir()
    {
        var env = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env)) return env;

        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 15 && dir != null; i++)
        {
            var kaggle = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(kaggle) && File.Exists(Path.Combine(kaggle, "Brasileirao_Matches.csv")))
                return kaggle;
            var parent = Directory.GetParent(dir)?.FullName;
            if (parent == null) break;
            dir = parent;
        }
        throw new DirectoryNotFoundException(
            $"Could not find data/kaggle starting from {AppContext.BaseDirectory}. " +
            "Set SOCCER_DATA_DIR to the folder containing the CSV files.");
    }
}
