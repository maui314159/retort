using System.Text.Json;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;
using ModelContextProtocol;

var dataDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "kaggle");
if (!Directory.Exists(dataDirectory))
{
    dataDirectory = Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
}

var soccerService = new SoccerDataService(dataDirectory);

var transport = new StdioServerTransport("BrazilianSoccerMcp", null);
var serverOptions = new McpServerOptions 
{ 
    ServerInfo = new Implementation { Name = "BrazilianSoccerMcp", Version = "1.0.0" } 
};

var server = McpServer.Create(transport, serverOptions, null, null);

// Tool: Search Matches
serverOptions.ToolCollection.Add(McpServerTool.Create(
    (SearchMatchesArgs args) => 
    {
        DateTime? start = string.IsNullOrWhiteSpace(args.StartDate) ? null : DateTime.Parse(args.StartDate);
        DateTime? end = string.IsNullOrWhiteSpace(args.EndDate) ? null : DateTime.Parse(args.EndDate);

        var results = soccerService.SearchSoccerMatches(args.Team, args.Competition, args.Season, start, end, args.Limit);
        if (results.Count == 0)
            return "No matches found matching the criteria.";

        var output = results.Select(m => $"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition}, Round/Stage: {m.Round})");
        return string.Join("\n", output);
    }, 
    new McpServerToolCreateOptions 
    { 
        Name = "search_matches",
        Description = "Search for soccer matches by team, competition, season, or date range."
    }));

// Tool: Get Team Statistics
serverOptions.ToolCollection.Add(McpServerTool.Create(
    (TeamStatsArgs args) => 
    {
        var stats = soccerService.GetTeamStatistics(args.Team, args.Season);
        var lines = new List<string> { $"{stats["Team"]} Statistics ({stats["Season"]}):" };
        lines.Add($"- Total Matches: {stats["TotalMatches"]}");
        lines.Add($"- Record: {stats["Wins"]}W - {stats["Draws"]}D - {stats["Losses"]}L");
        lines.Add($"- Goals: {stats["GoalsFor"]} For, {stats["GoalsAgainst"]} Against");
        lines.Add($"- Win Rate: {stats["WinRate"]}");
        lines.Add($"- Home Record: {stats["HomeRecord"]}");
        return string.Join("\n", lines);
    }, 
    new McpServerToolCreateOptions 
    { 
        Name = "get_team_statistics",
        Description = "Get win/loss/draw records, goals scored/conceded, and performance for a specific team."
    }));

// Tool: Search Players
serverOptions.ToolCollection.Add(McpServerTool.Create(
    (PlayerSearchArgs args) => 
    {
        var results = soccerService.SearchPlayers(args.Name, args.Nationality, args.Club, args.Position, args.Limit);
        if (results.Count == 0)
            return "No players found matching the criteria.";

        var output = results.Select((p, i) => $"{i + 1}. {p.Name} - Overall: {p.Overall}, Potential: {p.Potential}, Position: {p.Position}, Club: {p.Club}, Nationality: {p.Nationality}");
        return string.Join("\n", output);
    }, 
    new McpServerToolCreateOptions 
    { 
        Name = "search_players",
        Description = "Search for players by name, nationality, club, or position."
    }));

// Tool: Get Head to Head
serverOptions.ToolCollection.Add(McpServerTool.Create(
    (HeadToHeadArgs args) => 
    {
        var results = soccerService.GetHeadToHead(args.Team1, args.Team2, args.Season);
        if (results.Count <= 1)
            return "No head-to-head matches found between these teams.";

        var summary = results[0]["Summary"].ToString();
        var matches = results.Skip(1).Select(r => $"- {r["Date"]}: {r["HomeTeam"]} {r["Score"]} {r["AwayTeam"]} ({r["Competition"]}, {r["Round"]})");
        
        var output = new List<string> { $"Head-to-head: {summary}", "", "Recent matches:" };
        output.AddRange(matches);
        return string.Join("\n", output);
    }, 
    new McpServerToolCreateOptions 
    { 
        Name = "get_head_to_head",
        Description = "Compare two teams head-to-head, showing match history and summary."
    }));

// Tool: Get Statistical Analysis
serverOptions.ToolCollection.Add(McpServerTool.Create(
    (StatsAnalysisArgs args) => 
    {
        var stats = soccerService.GetStatisticalAnalysis(args.Competition, args.Season);
        if (stats.ContainsKey("Error"))
            return stats["Error"].ToString()!;

        var comp = string.IsNullOrWhiteSpace(args.Competition) ? "All Competitions" : args.Competition;
        var seas = string.IsNullOrWhiteSpace(args.Season) ? "All Seasons" : $"Season {args.Season}";
        
        var output = new List<string>
        {
            $"Statistical Analysis ({comp}, {seas}):",
            $"- Total Matches: {stats["TotalMatches"]}",
            $"- Average Goals per Match: {stats["AverageGoalsPerMatch"]}",
            $"- Home Win Rate: {stats["HomeWinRate"]}",
            "",
            "Biggest Wins:"
        };

        var biggestWins = (List<Dictionary<string, object>>)stats["BiggestWins"];
        output.AddRange(biggestWins.Select((w, i) => $"{i + 1}. {w["Date"]}: {w["MatchStr"]} ({w["Competition"]})"));
        return string.Join("\n", output);
    }, 
    new McpServerToolCreateOptions 
    { 
        Name = "get_statistical_analysis",
        Description = "Calculate aggregated statistics like average goals, home win rate, and biggest wins."
    }));

// Tool: Get Competition Standings
serverOptions.ToolCollection.Add(McpServerTool.Create(
    (StandingsArgs args) => 
    {
        var standings = soccerService.GetCompetitionStandings(args.Competition, args.Season);
        if (standings.Count == 0)
            return $"No standings available for {args.Competition} in {args.Season}.";

        var output = new List<string> { $"{args.Competition} {args.Season} Final Standings:" };
        
        foreach (var team in standings)
        {
            var isChampion = team["Pos"].ToString() == "1";
            var isRelegated = team["Pos"].ToString() == standings.Count.ToString() || 
                              team["Pos"].ToString() == (standings.Count - 1).ToString() || 
                              team["Pos"].ToString() == (standings.Count - 2).ToString() || 
                              team["Pos"].ToString() == (standings.Count - 3).ToString();
            
            var marker = isChampion ? " [CHAMPION]" : (isRelegated ? " [RELEGATED]" : "");
            output.Add($"{team["Pos"]}. {team["Team"]}{marker} - {team["Pts"]} pts ({team["W"]}W, {team["D"]}D, {team["L"]}L) | GD: {team["GD"]}");
        }
        return string.Join("\n", output);
    }, 
    new McpServerToolCreateOptions 
    { 
        Name = "get_competition_standings",
        Description = "Get calculated standings/league table for a specific competition and season."
    }));

await server.RunAsync();

// Argument classes
public class SearchMatchesArgs
{
    public string? Team { get; set; }
    public string? Competition { get; set; }
    public string? Season { get; set; }
    public string? StartDate { get; set; }
    public string? EndDate { get; set; }
    public int Limit { get; set; } = 50;
}

public class TeamStatsArgs
{
    public string Team { get; set; } = string.Empty;
    public string? Season { get; set; }
}

public class PlayerSearchArgs
{
    public string? Name { get; set; }
    public string? Nationality { get; set; }
    public string? Club { get; set; }
    public string? Position { get; set; }
    public int Limit { get; set; } = 50;
}

public class HeadToHeadArgs
{
    public string Team1 { get; set; } = string.Empty;
    public string Team2 { get; set; } = string.Empty;
    public string? Season { get; set; }
}

public class StatsAnalysisArgs
{
    public string? Competition { get; set; }
    public string? Season { get; set; }
}

public class StandingsArgs
{
    public string Competition { get; set; } = string.Empty;
    public string Season { get; set; } = string.Empty;
}
