// =============================================================================
// Brazilian Soccer MCP Server
// File: Program.cs
// Purpose: Process entry point. Loads the dataset once and starts the
//          stdio JSON-RPC 2.0 loop.
// Context: The server is started by an MCP host (e.g. Claude Desktop) which
//          spawns this process, then writes JSON-RPC requests to stdin
//          and reads responses from stdout. We never write logs to stdout
//          because that would corrupt the JSON-RPC stream -- any
//          diagnostics go to stderr.
// =============================================================================

using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Server;

var root = args.Length > 0 ? args[0] : Directory.GetCurrentDirectory();
Console.Error.WriteLine($"[BrazilianSoccerMcp] Loading dataset from {root} ...");
var dataset = Dataset.Load(root);
Console.Error.WriteLine(
    $"[BrazilianSoccerMcp] Loaded {dataset.Matches.Count} matches, {dataset.Players.Count} players.");

var server = new McpStdioServer(new QueryEngine(dataset));
await server.RunAsync(CancellationToken.None);
