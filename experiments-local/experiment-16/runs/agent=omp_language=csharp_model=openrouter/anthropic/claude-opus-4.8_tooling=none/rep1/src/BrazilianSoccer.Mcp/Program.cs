// =============================================================================
// Context: Brazilian Soccer MCP Server — host entry point.
//
// Boots a Model Context Protocol server over stdio. At startup it locates the
// data/kaggle directory (env var BRSOCCER_DATA_ROOT overrides; otherwise it
// walks up from the executable/cwd), loads all six CSVs into a SoccerData store,
// wraps it in a singleton QueryEngine, and registers the [McpServerTool] methods
// of SoccerTools. Logging goes to stderr so it never corrupts the stdio MCP
// channel (stdout is reserved for protocol JSON-RPC).
// =============================================================================
using BrazilianSoccer.Core;
using BrazilianSoccer.Mcp;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

// Route all logs to stderr; stdout carries the MCP protocol stream.
builder.Logging.ClearProviders();
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

// Resolve the data root: explicit env override, then walk up from the app base
// directory, then from the current working directory.
var dataRoot = ResolveDataRoot();
var data = SoccerData.Load(dataRoot);
builder.Services.AddSingleton(data);
builder.Services.AddSingleton(sp => new QueryEngine(sp.GetRequiredService<SoccerData>()));

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
return;

static string ResolveDataRoot()
{
    var env = Environment.GetEnvironmentVariable("BRSOCCER_DATA_ROOT");
    if (!string.IsNullOrWhiteSpace(env))
        return env;

    foreach (var start in new[] { AppContext.BaseDirectory, Directory.GetCurrentDirectory() })
    {
        try { return SoccerData.FindDataRoot(start); }
        catch (DirectoryNotFoundException) { /* try next */ }
    }

    throw new DirectoryNotFoundException(
        "Could not locate data/kaggle. Set BRSOCCER_DATA_ROOT to the repository root.");
}
