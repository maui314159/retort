// BrazilianSoccerMcp.Server - MCP server entry point.
// Hosts the tools from this assembly over the stdio MCP transport so an MCP
// client (e.g. Claude Desktop, an LLM agent) can invoke them. Logging is
// redirected to stderr to keep stdout reserved for the JSON-RPC protocol.
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

// MCP speaks JSON-RPC over stdout, so force all framework logs to stderr.
builder.Logging.AddFilter("Microsoft", LogLevel.Warning);
builder.Logging.AddFilter("System", LogLevel.Warning);
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
