using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Shared fixture: locates <c>data/kaggle</c> by walking up from the test
/// assembly and loads the <see cref="SoccerDataService"/> exactly once for
/// the whole test run (FIFA CSV is 9 MB, so per-class loads are wasteful).
/// </summary>
public static class TestData
{
    private static readonly Lazy<SoccerDataService> LazyService = new(() =>
        SoccerDataService.LoadFromDirectory(FindDataDir()));

    public static SoccerDataService Service => LazyService.Value;

    public static string FindDataDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (File.Exists(Path.Combine(candidate, "Brasileirao_Matches.csv")))
                return candidate;
            dir = dir.Parent;
        }
        throw new DirectoryNotFoundException("data/kaggle not found above " + AppContext.BaseDirectory);
    }
}
