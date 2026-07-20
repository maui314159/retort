using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;

// Brazilian Soccer MCP server entry point.
// Usage: BrazilianSoccerMcp [--data-dir <path-to-data/kaggle>]
// Data directory resolution: CLI arg, then BRAZILIAN_SOCCER_DATA_DIR, then repo discovery.

var log = Console.Error;

string? dataDir = null;
for (var i = 0; i < args.Length; i++)
{
    if (args[i] == "--data-dir" && i + 1 < args.Length)
        dataDir = args[++i];
}

try
{
    var resolvedDir = dataDir is not null && Directory.Exists(dataDir)
        ? Path.GetFullPath(dataDir)
        : DataLoader.ResolveDataDirectory();

    log.WriteLine("[brazilian-soccer-mcp] loading data from {0}", resolvedDir);
    var loader = DataLoader.LoadAll(resolvedDir);
    log.WriteLine("[brazilian-soccer-mcp] loaded {0} matches, {1} players",
        loader.Matches.Count, loader.Players.Count);

    var service = new SoccerDataService(loader);
    var tools = new ToolRegistry(service);
    var server = new McpServer(tools, Console.In, Console.Out, log);
    return await server.RunAsync();
}
catch (Exception ex)
{
    log.WriteLine("[brazilian-soccer-mcp] fatal: {0}", ex.Message);
    return 1;
}
