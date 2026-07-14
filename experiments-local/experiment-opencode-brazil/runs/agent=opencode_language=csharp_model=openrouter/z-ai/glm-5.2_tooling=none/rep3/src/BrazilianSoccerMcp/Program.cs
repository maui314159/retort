using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Services;

// Entry point for the Brazilian Soccer MCP server.
// On launch the server loads every CSV from data/kaggle/ (resolved relative
// to the working directory, with a fallback to the project root) and then
// speaks JSON-RPC 2.0 over stdio until the host closes stdin.

var kaggleDir = ResolveKaggleDir();
var repo = new DataRepository(kaggleDir);
repo.Load();

var matches = new MatchService(repo);
var teams = new TeamService(repo);
var players = new PlayerService(repo);
var competitions = new CompetitionService(repo);
var registry = new ToolRegistry(matches, teams, players, competitions);

var server = new McpServer(registry, Console.In, Console.Out);
server.Run();

static string ResolveKaggleDir()
{
    var candidates = new[]
    {
        Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle"),
        Path.Combine(AppContext.BaseDirectory, "data", "kaggle"),
        Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "data", "kaggle"),
    };
    foreach (var c in candidates)
    {
        if (Directory.Exists(c)) return Path.GetFullPath(c);
    }
    return candidates[0];
}
