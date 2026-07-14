// -----------------------------------------------------------------------------
// File: Program.cs
// Project: BrazilianSoccer.Server
//
// Context:
//   Entry point for the Brazilian Soccer MCP server. Hosts the official
//   ModelContextProtocol .NET SDK over the stdio transport so any MCP client
//   (Claude Desktop, an LLM agent, the MCP Inspector) can connect by launching
//   this executable and speaking JSON-RPC over stdin/stdout.
//
//   Critical stdio constraint: stdout is the MCP message channel, so ALL logging
//   MUST go to stderr. We configure the console logger to write to stderr and
//   leave stdout exclusively for protocol traffic.
//
//   Startup:
//     - Load every dataset once into a singleton SoccerDataStore (it is immutable
//       and shared across concurrent tool calls). The load resolves the data
//       directory via DataPaths (walks up from cwd / assembly, or honours the
//       BRAZILIAN_SOCCER_DATA env var).
//     - Register the query services as singletons so the tool classes receive
//       them by DI.
//     - Discover [McpServerToolType] classes in this assembly and expose their
//       [McpServerTool] methods.
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core;
using BrazilianSoccer.Core.Queries;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

// stdout is reserved for MCP JSON-RPC; route all logs to stderr.
builder.Logging.ClearProviders();
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

// Load all datasets once at startup; fail fast with a clear message if missing.
var store = SoccerDataStore.Load();

builder.Services.AddSingleton(store);
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
