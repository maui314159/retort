using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using ModelContextProtocol;
using ModelContextProtocol.Server;
using ModelContextProtocol.Protocol;

var dataPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory ?? Directory.GetCurrentDirectory(), "data", "kaggle");

var dataManager = new SoccerDataManager(dataPath);
await dataManager.LoadDataAsync();

var options = new McpServerOptions
{
    ServerInfo = new Implementation { Name = "BrazilianSoccerMcp", Version = "1.0.0" },
    Capabilities = new ServerCapabilities
    {
        Tools = new ()
    }
};

var tools = new List<McpServerTool>();

tools.Add(McpServerTool.Create((Func<string?, string?, string?, string?, string?, Task<string>>)(async (team, season, competition, dateFrom, dateTo) =>
{
    var matches = dataManager.SearchMatches(team, season, competition, dateFrom, dateTo);
    if (!matches.Any()) return "No matches found for the specified criteria.";

    var result = new List<string>();
    foreach (var m in matches.Take(20))
    {
        result.Add($"{m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals} - {m.AwayGoals} {m.AwayTeam} ({m.Competition}, {m.Season})");
    }
    if (matches.Count > 20) result.Add($"... and {matches.Count - 20} more matches.");
    return string.Join("\n", result);
}), new McpServerToolCreateOptions { Name = "search_matches", Description = "Searches for matches by team, date range, competition, or season" }));

tools.Add(McpServerTool.Create((Func<string, string?, Task<string>>)(async (team, season) =>
{
    var stats = dataManager.GetTeamStats(team, season);
    if (stats == null) return $"No data found for team '{team}'.";
    return $"Stats for {stats.Team} (Season: {stats.Season ?? "All"}):\n" +
           $"- Matches: {stats.Matches}\n" +
           $"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}\n" +
           $"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}\n" +
           $"- Win Rate: {stats.WinRate:P1}";
}), new McpServerToolCreateOptions { Name = "get_team_stats", Description = "Gets win/loss/draw records and goals for a specific team in a season" }));

tools.Add(McpServerTool.Create((Func<string, string, Task<string>>)(async (team1, team2) =>
{
    var h2h = dataManager.GetHeadToHead(team1, team2);
    if (h2h == null || h2h.Matches.Count == 0) return $"No matches found between {team1} and {team2}.";
    var result = new List<string>
    {
        $"Head-to-head: {h2h.Team1} {h2h.Team1Wins} wins, {h2h.Team2} {h2h.Team2Wins} wins, {h2h.Draws} draws",
        "Recent matches:"
    };
    foreach (var m in h2h.Matches.Take(10))
    {
        result.Add($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals} - {m.AwayGoals} {m.AwayTeam} ({m.Competition}, {m.Season})");
    }
    return string.Join("\n", result);
}), new McpServerToolCreateOptions { Name = "get_head_to_head", Description = "Gets head-to-head record and recent matches between two teams" }));

tools.Add(McpServerTool.Create((Func<string?, string?, string?, string?, int?, Task<string>>)(async (name, nationality, club, position, minOverall) =>
{
    var players = dataManager.SearchPlayers(name, nationality, club, position, minOverall);
    if (!players.Any()) return "No players found for the specified criteria.";
    var result = new List<string>();
    foreach (var p in players.Take(15))
    {
        result.Add($"- {p.Name} (Age: {p.Age}, Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}, Nationality: {p.Nationality})");
    }
    if (players.Count > 15) result.Add($"... and {players.Count - 15} more players.");
    return string.Join("\n", result);
}), new McpServerToolCreateOptions { Name = "search_players", Description = "Searches for players by name, nationality, club, position, or minimum overall rating" }));

tools.Add(McpServerTool.Create((Func<string, string, Task<string>>)(async (competition, season) =>
{
    var standings = dataManager.GetCompetitionStandings(competition, season);
    if (!standings.Any()) return $"No standings data found for {competition} in {season}.";
    var result = new List<string> { $"{competition} {season} Standings:" };
    foreach (var s in standings.Take(20))
    {
        result.Add($"{s.Rank}. {s.Team} - {s.Points} pts ({s.Wins}W, {s.Draws}D, {s.Losses}L, GF:{s.GoalsFor}, GA:{s.GoalsAgainst})");
    }
    return string.Join("\n", result);
}), new McpServerToolCreateOptions { Name = "get_competition_standings", Description = "Calculates standings for a competition in a specific season based on match results" }));

tools.Add(McpServerTool.Create((Func<string, Task<string>>)(async (type) =>
{
    var analysis = dataManager.GetStatisticalAnalysis(type.ToLowerInvariant());
    return analysis ?? "Unknown analysis type. Use 'average_goals', 'biggest_wins', or 'home_win_rate'.";
}), new McpServerToolCreateOptions { Name = "get_statistical_analysis", Description = "Provides statistical analysis like average goals, biggest wins, or home win rate" }));

options.ToolCollection = new McpServerPrimitiveCollection<McpServerTool>();
foreach (var tool in tools)
{
    options.ToolCollection.Add(tool);
}

var transport = new StdioServerTransport(options.ServerInfo.Name);
var server = McpServer.Create(transport, options);

await server.RunAsync();