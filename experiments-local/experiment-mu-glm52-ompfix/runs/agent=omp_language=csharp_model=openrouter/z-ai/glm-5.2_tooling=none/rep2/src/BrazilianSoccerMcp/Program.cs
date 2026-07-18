// ============================================================================
// BrazilianSoccerMcp - Program.cs
//
// Context block:
//   Entry point for the Brazilian Soccer MCP server. Hosts a stdio MCP server
//   using ModelContextProtocol SDK + Microsoft.Extensions.Hosting. On startup
//   it loads all six Kaggle CSV datasets into the in-memory SoccerDataStore
//   and registers SoccerQueryService + SoccerTools with the DI container.
//
//   Data directory resolution order:
//     1. SOCCER_DATA_DIR environment variable (absolute or relative to cwd).
//     2. ./data/kaggle relative to the current working directory.
//     3. ./data/kaggle relative to the AppContext.BaseDirectory (the bin
//        folder), where the .csproj copies the CSVs at build time.
//     4. Several ancestor directories of cwd (for `dotnet run` from repo root).
//   The first directory that contains at least one expected CSV file wins.
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var dataDir = ResolveDataDirectory();
var store = new SoccerDataStore(dataDir);

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddSingleton(store);
builder.Services.AddSingleton<SoccerQueryService>();
builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithTools<SoccerTools>();

// MCP stdio servers must not write logs to stdout (it carries the JSON-RPC
// stream), so console logs are redirected to stderr.
builder.Logging.AddConsole(options =>
{
    options.LogToStandardErrorThreshold = LogLevel.Trace;
});

await builder.Build().RunAsync();

// ----------------------------------------------------------------------
static string ResolveDataDirectory()
{
    var candidates = new List<string>();
    var envDir = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
    if (!string.IsNullOrWhiteSpace(envDir))
        candidates.Add(envDir!);

    candidates.Add(Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle"));
    candidates.Add(Path.Combine(AppContext.BaseDirectory, "data", "kaggle"));

    var dir = Directory.GetCurrentDirectory();
    for (int i = 0; i < 6 && !string.IsNullOrEmpty(dir); i++)
    {
        dir = Path.GetDirectoryName(dir);
        if (dir is null) break;
        candidates.Add(Path.Combine(dir, "data", "kaggle"));
    }

    foreach (var c in candidates)
    {
        try
        {
            var full = Path.GetFullPath(c);
            if (Directory.Exists(full) &&
                File.Exists(Path.Combine(full, "Brasileirao_Matches.csv")))
                return full;
        }
        catch { /* ignore path errors, try next */ }
    }

    // Fallback: return the first candidate even if it doesn't exist — the
    // store tolerates missing files and reports zero counts.
    return candidates[0];
}
