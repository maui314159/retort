using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ModelContextProtocol.Server;
using Microsoft.Extensions.Logging;

// Find the data directory: check CWD, then walk up
static string FindDataPath()
{
    var candidates = new List<string>();
    var dir = Directory.GetCurrentDirectory();
    for (int i = 0; i < 6; i++)
    {
        candidates.Add(Path.Combine(dir, "data", "kaggle"));
        var parent = Directory.GetParent(dir)?.FullName;
        if (parent == null) break;
        dir = parent;
    }

    var found = candidates.FirstOrDefault(Directory.Exists);
    if (found == null)
        throw new DirectoryNotFoundException(
            $"Cannot find 'data/kaggle' directory. Searched: {string.Join(", ", candidates)}");

    return found;
}

var dataPath = FindDataPath();

var builder = Host.CreateApplicationBuilder(args);

// Suppress non-error logging to keep stdio clean
builder.Logging.SetMinimumLevel(LogLevel.Warning);

builder.Services
    .AddSingleton(new DataRepository(dataPath))
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly(typeof(MatchTools).Assembly);

var host = builder.Build();

// Preload data before accepting connections
var repo = host.Services.GetRequiredService<DataRepository>();
await repo.LoadAsync();

await host.RunAsync();
