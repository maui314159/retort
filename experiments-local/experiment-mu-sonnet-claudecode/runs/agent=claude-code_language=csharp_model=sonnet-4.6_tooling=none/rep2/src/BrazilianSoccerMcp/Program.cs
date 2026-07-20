using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddSingleton<DataService>();

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithTools<MatchTools>()
    .WithTools<PlayerTools>()
    .WithTools<TeamTools>()
    .WithTools<StatsTools>();

var host = builder.Build();

await host.Services.GetRequiredService<DataService>().LoadAsync();

await host.RunAsync();
