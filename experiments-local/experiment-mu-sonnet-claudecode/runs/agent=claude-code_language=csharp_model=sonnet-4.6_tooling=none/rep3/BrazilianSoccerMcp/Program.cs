using BrazilianSoccerMcp;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var dataDir = Path.Combine(AppContext.BaseDirectory, "data", "kaggle");

// Walk up from BaseDirectory to find the data folder (handles running from project dir)
if (!Directory.Exists(dataDir))
{
    var dir = AppContext.BaseDirectory;
    while (dir != null && !Directory.Exists(Path.Combine(dir, "data", "kaggle")))
        dir = Directory.GetParent(dir)?.FullName;
    if (dir != null)
        dataDir = Path.Combine(dir, "data", "kaggle");
}

var db = new SoccerDatabase();
db.Initialize(dataDir);

var builder = Host.CreateApplicationBuilder(args);
builder.Logging.AddConsole(opts =>
{
    opts.LogToStandardErrorThreshold = LogLevel.Trace;
});

builder.Services.AddSingleton(db);
builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly(typeof(SoccerTools).Assembly);

await builder.Build().RunAsync();
