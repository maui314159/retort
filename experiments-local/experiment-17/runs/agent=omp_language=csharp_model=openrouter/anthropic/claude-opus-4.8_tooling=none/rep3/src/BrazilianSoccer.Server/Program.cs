// =============================================================================
// File:    Program.cs
// Project: BrazilianSoccer.Server
// Purpose: Entry point. Boots a Model Context Protocol server over stdio,
//          loads the Brazilian soccer datasets once into a shared
//          SoccerDatabase singleton, and registers the [McpServerTool] methods
//          in SoccerTools for discovery by an LLM client.
// Context: stdio transport is the standard MCP wiring for a local server an
//          assistant launches as a subprocess. All logging goes to stderr so
//          stdout stays a clean JSON-RPC channel. The data directory resolves
//          from (1) the SOCCER_DATA_DIR env var, (2) the first CLI arg, or
//          (3) a search up the directory tree for data/kaggle — so the server
//          works whether run from the repo root or its bin output folder.
// =============================================================================

using BrazilianSoccer.Core;
using BrazilianSoccer.Server;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

// MCP requires stdout to carry only protocol traffic; send logs to stderr.
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

var dataDir = DataDirectory.Resolve(args);
var database = SoccerDatabase.Load(dataDir);
Console.Error.WriteLine(
    $"[BrazilianSoccerMcp] Loaded {database.AllMatches.Count} matches and " +
    $"{database.AllPlayers.Count} players from {dataDir}");

builder.Services.AddSingleton(database);
builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

await builder.Build().RunAsync();

namespace BrazilianSoccer.Server
{
    internal static class DataDirectory
    {
        public static string Resolve(string[] args)
        {
            var fromEnv = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
            if (!string.IsNullOrWhiteSpace(fromEnv) && Directory.Exists(fromEnv)) return fromEnv;
            if (args.Length > 0 && Directory.Exists(args[0])) return args[0];

            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null)
            {
                var candidate = Path.Combine(dir.FullName, "data", "kaggle");
                if (Directory.Exists(candidate)) return candidate;
                dir = dir.Parent;
            }

            // Fall back to cwd-relative; loaders tolerate missing files.
            return Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
        }
    }
}
