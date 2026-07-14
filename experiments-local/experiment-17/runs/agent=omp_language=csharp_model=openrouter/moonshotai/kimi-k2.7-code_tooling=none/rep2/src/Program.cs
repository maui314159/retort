using BrazilianSoccerMcpServer.Services;
using BrazilianSoccerMcpServer.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddSingleton<SoccerDataService>();
builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithTools<SoccerTools>();

builder.Logging.AddConsole(options =>
{
    options.LogToStandardErrorThreshold = LogLevel.Trace;
});

await builder.Build().RunAsync();
