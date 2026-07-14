// ============================================================================
// File: Program.cs
// ----------------------------------------------------------------------------
// Context: Entry point for the Brazilian Soccer MCP server.
//
// Builds a generic .NET host that:
//   1. Loads all six CSV datasets once into a SoccerDataStore singleton.
//   2. Registers an MCP server over stdio (JSON-RPC) with all tool classes.
//   3. Routes all logging to stderr so stdout stays clean for the MCP protocol.
//
// The server is consumed by any MCP client (Claude, etc.) which lists and
// invokes the tools to answer natural-language questions about Brazilian
// soccer. See brazilian-soccer-mcp-guide.md / TASK.md for the full spec.
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

var builder = Host.CreateApplicationBuilder(args);

builder.Logging.AddConsole(options =>
{
    // MCP runs over stdio: log output MUST go to stderr, never stdout.
    options.LogToStandardErrorThreshold = LogLevel.Trace;
});

// Load datasets once and share across all tool instances.
builder.Services.AddSingleton<SoccerDataStore>();

builder.Services
    .AddMcpServer(options =>
    {
        options.ServerInfo = new Implementation
        {
            Name = "brazilian-soccer-mcp",
            Version = "1.0.0",
            Title = "Brazilian Soccer MCP Server",
            Description = "Query Brazilian soccer matches, teams, players and competitions.",
        };
    })
    .WithStdioServerTransport()
    .WithTools<MatchTools>()
    .WithTools<TeamTools>()
    .WithTools<PlayerTools>()
    .WithTools<CompetitionTools>()
    .WithTools<StatisticsTools>();

await builder.Build().RunAsync();
