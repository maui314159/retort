// Context: Brazilian Soccer MCP Server.
// Entry point. Loads the six Kaggle CSVs into memory, builds the knowledge
// graph, and hosts an MCP server over stdio (JSON-RPC 2.0) via the official
// ModelContextProtocol C# SDK. All logging goes to stderr so stdout carries
// only protocol messages. Data directory resolution: --data arg,
// BRAZILIAN_SOCCER_DATA env var, ./data/kaggle, or walk-up search.
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;
using BrazilianSoccerMcp.Query;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var dataArg = args.SkipWhile(a => a != "--data").Skip(1).FirstOrDefault();
var dataDir = SoccerData.ResolveDataDir(dataArg);

var sw = System.Diagnostics.Stopwatch.StartNew();
var data = SoccerData.Load(dataDir);
var graph = SoccerKnowledgeGraph.Build(data);
await Console.Error.WriteLineAsync(
    $"[brazilian-soccer-mcp] Loaded {data.Matches.Count} matches, {data.Players.Count} players, " +
    $"{graph.Teams.Count} teams from {dataDir} in {sw.ElapsedMilliseconds} ms");

var builder = Host.CreateApplicationBuilder(args);
builder.Logging.ClearProviders();
builder.Logging.AddConsole(options => options.LogToStandardErrorThreshold = LogLevel.Trace);

builder.Services.AddSingleton(data);
builder.Services.AddSingleton(graph);
builder.Services.AddSingleton<SoccerQueryEngine>();
builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();
