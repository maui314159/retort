// Brazilian Soccer MCP Server - Entry point
//
// Context: This program hosts the MCP server over stdio transport, the standard
// way an MCP server is launched by a client (e.g. Claude, Copilot). The server
// is a .NET generic Host that:
//   1. Configures logging to stderr (MCP stdio reserves stdout for protocol).
//   2. Registers SoccerDataService as a singleton (eagerly loads CSVs once).
//   3. Registers the MCP server with stdio transport and discovers all
//      [McpServerToolType] classes in this assembly via WithToolsFromAssembly.
// Tool classes (MatchTools, SoccerTools) take SoccerDataService via constructor;
// WithToolsFromAssembly uses ActivatorUtilities.CreateInstance to build them, so
// the DI-registered service is injected automatically.

using BrazilianSoccerMcp.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

var builder = Host.CreateApplicationBuilder(args);

// MCP stdio servers must reserve stdout for JSON-RPC protocol messages; all
// diagnostic logging goes to stderr so it doesn't corrupt the protocol stream.
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

// Register the data service as a singleton so all tool invocations share one
// in-memory copy of the datasets.
builder.Services.AddSingleton<SoccerDataService>();

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
