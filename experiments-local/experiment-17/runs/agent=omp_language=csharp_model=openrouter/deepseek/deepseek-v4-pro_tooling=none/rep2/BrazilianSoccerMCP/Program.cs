using BrazilianSoccerMCP.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ModelContextProtocol.Server;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddMcpServer(options =>
{
    options.ServerInfo = new()
    {
        Name = "Brazilian Soccer MCP Server",
        Version = "1.0.0"
    };
})
.WithStdioServerTransport()
.WithTools<SoccerTools>();

var host = builder.Build();
await host.RunAsync();
