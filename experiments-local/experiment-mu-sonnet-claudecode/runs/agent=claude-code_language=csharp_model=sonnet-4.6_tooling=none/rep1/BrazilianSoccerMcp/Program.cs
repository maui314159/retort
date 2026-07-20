using BrazilianSoccerMcp;
using BrazilianSoccerMcp.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

builder.Logging.AddConsole(options =>
{
    options.LogToStandardErrorThreshold = LogLevel.Trace;
});

builder.Services.AddSingleton<SoccerDataService>(_ =>
{
    var dataPath = DataPathFinder.FindKaggleDataPath();
    return SoccerDataService.LoadFromDisk(dataPath);
});

builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
