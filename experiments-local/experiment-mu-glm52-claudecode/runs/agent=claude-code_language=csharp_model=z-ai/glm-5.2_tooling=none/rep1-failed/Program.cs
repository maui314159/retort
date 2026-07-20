// =============================================================================
// File: Program.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — entry point.
//   Builds a .NET generic host that exposes the BrazilianSoccerTools over the
//   Model Context Protocol on stdio. The SoccerDatabase is built once at
//   startup (singleton) and injected into every query service, which are in
//   turn injected into the tool class.
//
//   Stdio is the only transport: MCP clients (Claude Desktop, Claude Code,
//   etc.) launch this process and communicate via JSON-RPC on stdin/stdout.
//   All logging goes to stderr so it never corrupts the JSON-RPC stream on
//   stdout.
//
//   Configure the data directory with the BRAZILIAN_SOCCER_DATA env var, or
//   leave it unset to auto-resolve (see SoccerDatabase.ResolveDataDir).
// =============================================================================
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Query;
using BrazilianSoccerMcp.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

builder.Logging.AddConsole(consoleLogOptions =>
{
    // MCP runs JSON-RPC on stdout; ALL logs must go to stderr.
    consoleLogOptions.LogToStandardErrorThreshold = LogLevel.Trace;
});

// Build the in-memory soccer database once and share it across every request.
builder.Services.AddSingleton<SoccerDatabase>();
builder.Services.AddSingleton<MatchQueryService>();
builder.Services.AddSingleton<TeamQueryService>();
builder.Services.AddSingleton<PlayerQueryService>();
builder.Services.AddSingleton<CompetitionQueryService>();
builder.Services.AddSingleton<StatisticsService>();

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
