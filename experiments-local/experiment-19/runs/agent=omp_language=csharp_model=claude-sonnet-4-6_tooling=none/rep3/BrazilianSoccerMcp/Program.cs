using BrazilianSoccerMcp.Data;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

// Locate the CSV data directory by walking up from the executable
var dataDir = FindDataDirectory();

var builder = Host.CreateApplicationBuilder(args);

// All logs go to stderr so they don't corrupt the stdio MCP channel
builder.Logging.AddConsole(opts =>
{
    opts.LogToStandardErrorThreshold = LogLevel.Trace;
});

builder.Services.AddSingleton(_ =>
{
    var repo = new DataRepository(dataDir);
    return repo;
});

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();

// ---------------------------------------------------------------------------
static string FindDataDirectory()
{
    var envPath = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
    if (!string.IsNullOrEmpty(envPath) && Directory.Exists(envPath))
        return envPath;

    // Walk up from the executable directory
    var dir = new DirectoryInfo(AppContext.BaseDirectory);
    while (dir is not null)
    {
        var candidate = Path.Combine(dir.FullName, "data", "kaggle");
        if (Directory.Exists(candidate))
            return candidate;
        dir = dir.Parent;
    }

    // Walk up from the current working directory
    dir = new DirectoryInfo(Directory.GetCurrentDirectory());
    while (dir is not null)
    {
        var candidate = Path.Combine(dir.FullName, "data", "kaggle");
        if (Directory.Exists(candidate))
            return candidate;
        dir = dir.Parent;
    }

    throw new InvalidOperationException(
        "Cannot find data/kaggle directory. " +
        "Set the SOCCER_DATA_DIR environment variable to the directory containing the CSV files.");
}
