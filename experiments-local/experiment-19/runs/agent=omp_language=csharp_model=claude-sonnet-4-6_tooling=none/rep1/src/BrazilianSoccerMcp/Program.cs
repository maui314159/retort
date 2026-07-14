using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

var dataPath = ResolveDataPath();
if (dataPath is null)
{
    await Console.Error.WriteLineAsync(
        "ERROR: Cannot find 'data/kaggle' directory.\n" +
        "Set the DATA_PATH environment variable to the directory containing the CSV files.");
    return 1;
}

var builder = Host.CreateApplicationBuilder(args);

// Suppress noisy default logging so it doesn't pollute the MCP stdio stream
builder.Logging.SetMinimumLevel(Microsoft.Extensions.Logging.LogLevel.Warning);

// Load all CSV data once at startup
builder.Services.AddSingleton(_ => DataRepository.LoadFromCsvs(dataPath));

// Register tool classes so DI can inject DataRepository into them
builder.Services.AddTransient<MatchTools>();
builder.Services.AddTransient<PlayerTools>();

builder.Services.AddMcpServer(options =>
{
    options.ServerInfo = new ModelContextProtocol.Protocol.Implementation
    {
        Name    = "BrazilianSoccerMcp",
        Version = "1.0.0",
    };
})
.WithStdioServerTransport()
.WithTools<MatchTools>()
.WithTools<PlayerTools>();

await builder.Build().RunAsync();
return 0;

// ─── helper ───────────────────────────────────────────────────────────────────

static string? ResolveDataPath()
{
    // 1. Explicit env var
    var env = Environment.GetEnvironmentVariable("DATA_PATH");
    if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env)) return env;

    // 2. Walk up from cwd until we find data/kaggle
    var dir = Directory.GetCurrentDirectory();
    for (int depth = 0; depth < 6; depth++)
    {
        var candidate = Path.Combine(dir, "data", "kaggle");
        if (Directory.Exists(candidate)) return candidate;
        var parent = Directory.GetParent(dir)?.FullName;
        if (parent is null) break;
        dir = parent;
    }

    // 3. Walk up from the executable location
    dir = AppDomain.CurrentDomain.BaseDirectory;
    for (int depth = 0; depth < 8; depth++)
    {
        var candidate = Path.Combine(dir, "data", "kaggle");
        if (Directory.Exists(candidate)) return candidate;
        var parent = Directory.GetParent(dir)?.FullName;
        if (parent is null) break;
        dir = parent;
    }

    return null;
}
