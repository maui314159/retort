// =============================================================================
// BrazilianSoccerMcp - MCP Server Host
// -----------------------------------------------------------------------------
// Context: Entry point for the Brazilian Soccer MCP server. It resolves the
// Kaggle data directory, loads every CSV once into a singleton repository, and
// starts the MCP server over the stdio transport so a connected LLM client can
// discover and call the tools in BrazilianSoccerMcp.Tools.
//
// The data directory is resolved by walking upward from the current working
// directory and the executable directory until a folder named "data/kaggle"
// containing "Brasileirao_Matches.csv" is found. It can be overridden with the
// SOCCER_DATA_DIR environment variable.
//
// Logging is sent to stderr so it never corrupts the JSON-RPC stream on stdout.
// =============================================================================

using BrazilianSoccerMcp.Data;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

var dataDir = ResolveDataDirectory();
builder.Services.AddSingleton(new SoccerDataRepository(dataDir));
builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();

// ---------------------------------------------------------------------------

static string ResolveDataDirectory()
{
    var env = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
    if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env)) return env;

    var markers = new[] { "Brasileirao_Matches.csv" };
    var candidates = new List<string> { Directory.GetCurrentDirectory(), AppContext.BaseDirectory };
    foreach (var root in candidates)
    {
        var found = WalkUp(root, markers);
        if (found != null) return found;
    }
    throw new DirectoryNotFoundException(
        "Could not locate the data/kaggle directory. Set SOCCER_DATA_DIR to the folder " +
        "containing Brasileirao_Matches.csv and the other CSV files.");
}

static string? WalkUp(string start, string[] markers)
{
    var dir = start;
    for (int i = 0; i < 12 && dir != null; i++)
    {
        var kaggle = Path.Combine(dir, "data", "kaggle");
        if (Directory.Exists(kaggle) && markers.All(m => File.Exists(Path.Combine(kaggle, m))))
            return kaggle;
        var parent = Directory.GetParent(dir)?.FullName;
        dir = parent ?? "";
        if (dir.Length == 0) break;
    }
    return null;
}
