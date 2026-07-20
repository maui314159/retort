using BrazilianSoccerMcp.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp;

/// <summary>
/// Entry point: stdio MCP server exposing Brazilian soccer data tools.
/// All logs go to stderr; stdout is reserved for the MCP transport.
/// </summary>
public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        string dataDir;
        try
        {
            dataDir = ResolveDataDir(args);
        }
        catch (Exception ex)
        {
            await Console.Error.WriteLineAsync($"[brazilian-soccer-mcp] {ex.Message}");
            return 1;
        }

        var builder = Host.CreateApplicationBuilder(args);

        // MCP over stdio: everything log-related must go to stderr.
        builder.Logging.ClearProviders();
        builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);
        builder.Logging.SetMinimumLevel(LogLevel.Information);

        builder.Services.AddSingleton(_ => SoccerDataService.LoadFromDirectory(dataDir));
        builder.Services
            .AddMcpServer()
            .WithStdioServerTransport()
            .WithToolsFromAssembly();

        var app = builder.Build();

        // Warm the data store before serving so the first tool call is fast.
        var data = app.Services.GetRequiredService<SoccerDataService>();
        var logger = app.Services.GetRequiredService<ILoggerFactory>()
            .CreateLogger("BrazilianSoccerMcp");
        logger.LogInformation("Loaded {MatchCount} matches and {PlayerCount} players from {DataDir}",
            data.Matches.Count, data.Players.Count, dataDir);

        await app.RunAsync();
        return 0;
    }

    /// <summary>
    /// Locates the <c>data/kaggle</c> directory. Precedence:
    /// 1. <c>--data-dir</c> command-line argument
    /// 2. <c>SOCCER_DATA_DIR</c> environment variable
    /// 3. Walk up from the current directory / executable location looking for <c>data/kaggle</c>.
    /// </summary>
    public static string ResolveDataDir(string[] args)
    {
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == "--data-dir" && Directory.Exists(args[i + 1]))
                return Path.GetFullPath(args[i + 1]);
        }

        var env = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return Path.GetFullPath(env);

        var candidates = new[]
        {
            Directory.GetCurrentDirectory(),
            AppContext.BaseDirectory,
        };

        foreach (var start in candidates)
        {
            var dir = new DirectoryInfo(start);
            while (dir is not null)
            {
                var candidate = Path.Combine(dir.FullName, "data", "kaggle");
                if (Directory.Exists(candidate) &&
                    File.Exists(Path.Combine(candidate, "Brasileirao_Matches.csv")))
                    return candidate;
                dir = dir.Parent;
            }
        }

        throw new DirectoryNotFoundException(
            "Could not locate the 'data/kaggle' directory. Set SOCCER_DATA_DIR or pass --data-dir <path>.");
    }
}
