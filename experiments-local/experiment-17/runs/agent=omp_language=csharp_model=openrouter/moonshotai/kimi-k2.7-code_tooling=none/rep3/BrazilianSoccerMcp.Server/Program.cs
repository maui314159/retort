using BrazilianSoccerMcp.Server.Data;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

var builder = Host.CreateApplicationBuilder(args);

builder.Logging.AddConsole(consoleLogOptions =>
{
    consoleLogOptions.LogToStandardErrorThreshold = LogLevel.Trace;
});

builder.Services.AddSingleton<SoccerDataContext>(_ =>
{
    var dataDirectory = GetDataDirectory();
    return new DataLoader(dataDirectory).Load();
});

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();

static string GetDataDirectory()
{
    var assemblyLocation = System.Reflection.Assembly.GetExecutingAssembly().Location;
    var assemblyDirectory = Path.GetDirectoryName(assemblyLocation)!;

    // When published, data is copied next to the executable
    var publishedData = Path.Combine(assemblyDirectory, "data", "kaggle");
    if (Directory.Exists(publishedData))
    {
        return publishedData;
    }

    // Fallback to repository layout when running from project directory
    var repoData = Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
    if (Directory.Exists(repoData))
    {
        return repoData;
    }

    var parentRepoData = Path.Combine(Directory.GetCurrentDirectory(), "..", "data", "kaggle");
    if (Directory.Exists(parentRepoData))
    {
        return Path.GetFullPath(parentRepoData);
    }

    throw new DirectoryNotFoundException("Could not find data/kaggle directory.");
}
