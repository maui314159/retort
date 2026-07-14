// Brazilian Soccer MCP Server - Entry point
// Context: Hosts the MCP server over stdio using the official ModelContextProtocol
// C# SDK. Logging is redirected to stderr so stdout stays clean for the JSON-RPC
// MCP framing. Tools are discovered from the assembly via WithToolsFromAssembly(),
// which picks up every [McpServerToolType] class (SoccerTools). The datasets are
// loaded lazily on first tool invocation (see SoccerTools.Service), keeping cold
// start fast and confining parse cost to the first query.

using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

var builder = Host.CreateApplicationBuilder(args);

builder.Logging.AddConsole(consoleLogOptions =>
{
    // MCP stdio transport reserves stdout for protocol messages; send all logs to stderr.
    consoleLogOptions.LogToStandardErrorThreshold = LogLevel.Trace;
});

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
