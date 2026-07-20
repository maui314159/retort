using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Shared fixture: loads the real Kaggle datasets once for the whole test run.
/// The load takes ~1 second, so every feature test exercises actual data.
/// </summary>
public static class TestData
{
    private static readonly Lazy<KnowledgeGraph> LazyGraph = new(() =>
    {
        var dir = FindDataDir();
        return new KnowledgeGraph(DataLoader.Load(dir));
    });

    public static KnowledgeGraph Graph => LazyGraph.Value;

    private static string FindDataDir()
    {
        foreach (var start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        {
            var dir = new DirectoryInfo(start);
            for (var depth = 0; dir is not null && depth < 10; depth++, dir = dir.Parent)
            {
                var candidate = Path.Combine(dir.FullName, "data", "kaggle");
                if (Directory.Exists(candidate) && File.Exists(Path.Combine(candidate, "fifa_data.csv")))
                    return candidate;
            }
        }
        throw new DirectoryNotFoundException("Could not locate data/kaggle from the test working directory.");
    }
}
