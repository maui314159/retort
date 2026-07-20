using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp;

/// <summary>
/// Entry point. Loads the six Kaggle CSVs from data/kaggle (located via the
/// BRAZILIAN_SOCCER_DATA_DIR environment variable or by walking up from the
/// executable), builds the knowledge graph, and serves MCP over stdio.
/// All diagnostics go to stderr; stdout carries only protocol messages.
/// </summary>
public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;

        var dataDir = ResolveDataDir(args);
        if (dataDir is null)
        {
            Console.Error.WriteLine(
                "error: could not locate the data/kaggle directory. " +
                "Set BRAZILIAN_SOCCER_DATA_DIR or run from within the repository.");
            return 1;
        }

        Console.Error.WriteLine($"[brazilian-soccer-mcp] loading data from {dataDir}");
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var data = DataLoader.Load(dataDir);
        var graph = new KnowledgeGraph(data);
        sw.Stop();
        Console.Error.WriteLine(
            $"[brazilian-soccer-mcp] ready: {graph.Matches.Count} matches, {graph.Players.Count} players, " +
            $"{graph.Teams.Count} teams in {sw.ElapsedMilliseconds} ms");

        var server = new McpServer(new ToolRegistry(graph));
        await server.RunAsync(Console.OpenStandardInput(), Console.OpenStandardOutput());
        return 0;
    }

    internal static string? ResolveDataDir(string[] args)
    {
        // 1. Explicit command-line override: --data-dir <path>
        for (var i = 0; i + 1 < args.Length; i++)
            if (args[i] == "--data-dir" && IsDataDir(args[i + 1]))
                return Path.GetFullPath(args[i + 1]);

        // 2. Environment variable.
        var env = Environment.GetEnvironmentVariable("BRAZILIAN_SOCCER_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(env) && IsDataDir(env))
            return Path.GetFullPath(env);

        // 3. Walk up from the current working directory, then from the executable.
        foreach (var start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        {
            var dir = new DirectoryInfo(start);
            for (var depth = 0; dir is not null && depth < 8; depth++, dir = dir.Parent)
            {
                var candidate = Path.Combine(dir.FullName, "data", "kaggle");
                if (IsDataDir(candidate))
                    return candidate;
            }
        }

        return null;
    }

    private static bool IsDataDir(string path) =>
        Directory.Exists(path) && File.Exists(Path.Combine(path, "fifa_data.csv"));
}
