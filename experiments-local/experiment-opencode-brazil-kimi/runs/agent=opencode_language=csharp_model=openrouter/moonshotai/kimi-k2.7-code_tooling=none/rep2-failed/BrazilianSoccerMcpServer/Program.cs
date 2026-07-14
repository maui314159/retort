using System.Text.Json;
using BrazilianSoccerMcpServer.Data;
using BrazilianSoccerMcpServer.Models;
using BrazilianSoccerMcpServer.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcpServer;

public class Program
{
    public static async Task Main(string[] args)
    {
        var basePath = FindDataRoot(Directory.GetCurrentDirectory());
        var store = CsvLoader.LoadFromDirectory(basePath);
        var queryService = new SoccerQueryService(store);

        var builder = Host.CreateApplicationBuilder(args);
        builder.Services.AddSingleton(queryService);
        builder.Services.AddSingleton(store);
        builder.Services.AddMcpServer()
            .WithStdioServerTransport()
            .WithListToolsHandler(ListToolsAsync)
            .WithCallToolHandler(CallToolAsync);

        var host = builder.Build();
        await host.RunAsync();
    }

    private static ValueTask<ListToolsResult> ListToolsAsync(RequestContext<ListToolsRequestParams> request, CancellationToken cancellationToken)
    {
        var tools = new List<Tool>
        {
            CreateTool("find_matches", "Find matches by team, opponent, competition, season, date range, round, or stage.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["properties"] = new Dictionary<string, object>
                {
                    ["team"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Team name to search for (home, away, or either)." },
                    ["opponent"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Optional opponent name." },
                    ["competition"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Competition name, e.g., Brasileirão, Copa do Brasil, Copa Libertadores." },
                    ["season"] = new Dictionary<string, object> { ["type"] = "integer", ["description"] = "Season year." },
                    ["from"] = new Dictionary<string, object> { ["type"] = "string", ["format"] = "date", ["description"] = "Start date (YYYY-MM-DD)." },
                    ["to"] = new Dictionary<string, object> { ["type"] = "string", ["format"] = "date", ["description"] = "End date (YYYY-MM-DD)." },
                    ["round"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Match round or label." },
                    ["stage"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Tournament stage (e.g., group stage, final)." },
                    ["limit"] = new Dictionary<string, object> { ["type"] = "integer", ["description"] = "Maximum number of results." },
                }
            }),
            CreateTool("last_match_between", "Find the most recent match between two teams.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["required"] = new[] { "teamA", "teamB" },
                ["properties"] = new Dictionary<string, object>
                {
                    ["teamA"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["teamB"] = new Dictionary<string, object> { ["type"] = "string" },
                }
            }),
            CreateTool("head_to_head", "Get head-to-head statistics between two teams.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["required"] = new[] { "teamA", "teamB" },
                ["properties"] = new Dictionary<string, object>
                {
                    ["teamA"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["teamB"] = new Dictionary<string, object> { ["type"] = "string" },
                }
            }),
            CreateTool("team_statistics", "Get win/loss/draw and goal statistics for a team, optionally filtered by season, competition, home/away.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["required"] = new[] { "team" },
                ["properties"] = new Dictionary<string, object>
                {
                    ["team"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["season"] = new Dictionary<string, object> { ["type"] = "integer" },
                    ["competition"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["homeOnly"] = new Dictionary<string, object> { ["type"] = "boolean" },
                    ["awayOnly"] = new Dictionary<string, object> { ["type"] = "boolean" },
                }
            }),
            CreateTool("league_standings", "Calculate league standings for a season and competition.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["required"] = new[] { "season" },
                ["properties"] = new Dictionary<string, object>
                {
                    ["season"] = new Dictionary<string, object> { ["type"] = "integer" },
                    ["competition"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["limit"] = new Dictionary<string, object> { ["type"] = "integer", ["description"] = "Number of positions to return." },
                }
            }),
            CreateTool("relegated_teams", "Get the teams relegated in a season.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["required"] = new[] { "season" },
                ["properties"] = new Dictionary<string, object>
                {
                    ["season"] = new Dictionary<string, object> { ["type"] = "integer" },
                    ["competition"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Defaults to Brasileirão." },
                }
            }),
            CreateTool("biggest_wins", "Get the biggest wins by goal difference.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["properties"] = new Dictionary<string, object>
                {
                    ["competition"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["season"] = new Dictionary<string, object> { ["type"] = "integer" },
                    ["limit"] = new Dictionary<string, object> { ["type"] = "integer" },
                }
            }),
            CreateTool("global_statistics", "Get overall statistics such as average goals, home win rate, etc.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["properties"] = new Dictionary<string, object>
                {
                    ["competition"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["season"] = new Dictionary<string, object> { ["type"] = "integer" },
                }
            }),
            CreateTool("find_players", "Search for players by name, nationality, club, or position.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["properties"] = new Dictionary<string, object>
                {
                    ["name"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["nationality"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Country name, e.g., Brazil." },
                    ["club"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["position"] = new Dictionary<string, object> { ["type"] = "string", ["description"] = "Position abbreviation, e.g., ST, LW, GK." },
                    ["minOverall"] = new Dictionary<string, object> { ["type"] = "integer" },
                    ["limit"] = new Dictionary<string, object> { ["type"] = "integer" },
                }
            }),
            CreateTool("top_players", "Get top rated players, optionally filtered by nationality, club, or position.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["properties"] = new Dictionary<string, object>
                {
                    ["nationality"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["club"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["position"] = new Dictionary<string, object> { ["type"] = "string" },
                    ["limit"] = new Dictionary<string, object> { ["type"] = "integer" },
                }
            }),
            CreateTool("competitions_for_team", "List competitions a team has played in.", new Dictionary<string, object>
            {
                ["type"] = "object",
                ["required"] = new[] { "team" },
                ["properties"] = new Dictionary<string, object>
                {
                    ["team"] = new Dictionary<string, object> { ["type"] = "string" },
                }
            }),
        };

        return new ValueTask<ListToolsResult>(new ListToolsResult { Tools = tools });
    }

    private static ValueTask<CallToolResult> CallToolAsync(RequestContext<CallToolRequestParams> request, CancellationToken cancellationToken)
    {
        var queryService = request.Services!.GetRequiredService<SoccerQueryService>();
        var args = request.Params.Arguments ?? new Dictionary<string, JsonElement>();

        string resultText = request.Params.Name switch
        {
            "find_matches" => FindMatches(queryService, args),
            "last_match_between" => LastMatchBetween(queryService, args),
            "head_to_head" => HeadToHead(queryService, args),
            "team_statistics" => TeamStatistics(queryService, args),
            "league_standings" => LeagueStandings(queryService, args),
            "relegated_teams" => RelegatedTeams(queryService, args),
            "biggest_wins" => BiggestWins(queryService, args),
            "global_statistics" => GlobalStatistics(queryService, args),
            "find_players" => FindPlayers(queryService, args),
            "top_players" => TopPlayers(queryService, args),
            "competitions_for_team" => CompetitionsForTeam(queryService, args),
            _ => $"Unknown tool: {request.Params.Name}"
        };

        var isError = resultText.StartsWith("Error:", StringComparison.OrdinalIgnoreCase);
        return new ValueTask<CallToolResult>(new CallToolResult
        {
            Content = new List<ContentBlock> { new TextContentBlock { Text = resultText } },
            IsError = isError,
        });
    }

    private static Tool CreateTool(string name, string description, Dictionary<string, object> schema)
    {
        return new Tool
        {
            Name = name,
            Description = description,
            InputSchema = JsonSerializer.SerializeToElement(schema),
        };
    }

    private static string FindMatches(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var team = GetString(args, "team");
        var opponent = GetString(args, "opponent");
        var competition = GetString(args, "competition");
        var season = GetInt(args, "season");
        var fromDate = GetDate(args, "from");
        var toDate = GetDate(args, "to");
        var round = GetString(args, "round");
        var stage = GetString(args, "stage");
        var limit = GetInt(args, "limit") ?? 50;

        var matches = service.FindMatches(team, opponent, competition, season, fromDate, toDate, round, stage, limit);
        return FormatMatches(matches);
    }

    private static string LastMatchBetween(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var teamA = GetString(args, "teamA");
        var teamB = GetString(args, "teamB");
        if (string.IsNullOrWhiteSpace(teamA) || string.IsNullOrWhiteSpace(teamB))
            return "Error: teamA and teamB are required.";
        var match = service.LastMatchBetween(teamA, teamB);
        if (match == null) return "No matches found.";
        return $"{match.Date:yyyy-MM-dd}: {match.FormatScore()} ({match.Competition}{(!string.IsNullOrWhiteSpace(match.Round) ? $" Round {match.Round}" : "")})";
    }

    private static string HeadToHead(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var teamA = GetString(args, "teamA");
        var teamB = GetString(args, "teamB");
        if (string.IsNullOrWhiteSpace(teamA) || string.IsNullOrWhiteSpace(teamB))
            return "Error: teamA and teamB are required.";
        var h2h = service.GetHeadToHead(teamA, teamB);
        var lines = new List<string>
        {
            $"{h2h.TeamA} vs {h2h.TeamB}:",
            $"Total matches in dataset: {h2h.Matches}",
            $"{h2h.TeamA} wins: {h2h.WinsA}, {h2h.TeamB} wins: {h2h.WinsB}, Draws: {h2h.Draws}",
            $"Goals: {h2h.TeamA} {h2h.GoalsA} - {h2h.GoalsB} {h2h.TeamB}",
        };
        if (h2h.MatchesList.Count > 0)
        {
            lines.Add("Recent matches:");
            lines.AddRange(h2h.MatchesList.Take(10).Select(m => $"- {m.Date:yyyy-MM-dd}: {m.FormatScore()} ({m.Competition})"));
        }
        return string.Join("\n", lines);
    }

    private static string TeamStatistics(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var team = GetString(args, "team");
        var season = GetInt(args, "season");
        var competition = GetString(args, "competition");
        var homeOnly = GetBool(args, "homeOnly") == true;
        var awayOnly = GetBool(args, "awayOnly") == true;
        if (string.IsNullOrWhiteSpace(team))
            return "Error: team is required.";
        var stats = service.GetTeamStatistics(team, season, competition, homeOnly, awayOnly);
        return FormatTeamStatistics(stats);
    }

    private static string LeagueStandings(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var season = GetInt(args, "season");
        var competition = GetString(args, "competition");
        var limit = GetInt(args, "limit") ?? 20;
        if (season == null)
            return "Error: season is required.";
        var standings = service.GetLeagueStandings(season.Value, competition).Take(limit).ToList();
        if (standings.Count == 0)
            return "No standings found.";
        var lines = new List<string> { $"Standings ({season.Value} {(competition ?? "all competitions")}):" };
        for (int i = 0; i < standings.Count; i++)
        {
            var s = standings[i];
            lines.Add($"{i + 1}. {s.Team} - {s.Points} pts ({s.Wins}W, {s.Draws}D, {s.Losses}L), GF {s.GoalsFor}, GA {s.GoalsAgainst}, GD {s.GoalsFor - s.GoalsAgainst}");
        }
        return string.Join("\n", lines);
    }

    private static string RelegatedTeams(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var season = GetInt(args, "season");
        var competition = GetString(args, "competition");
        if (season == null)
            return "Error: season is required.";
        var relegated = service.GetRelegatedTeams(season.Value, competition);
        if (relegated.Count == 0)
            return "No standings available.";
        return $"Relegated teams ({season.Value} {competition ?? "Brasileirão"}):\n" + string.Join("\n", relegated.Select(r => $"- {r.Team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L)"));
    }

    private static string BiggestWins(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var competition = GetString(args, "competition");
        var season = GetInt(args, "season");
        var limit = GetInt(args, "limit") ?? 10;
        var matches = service.GetBiggestWins(competition, season, limit);
        return FormatMatches(matches);
    }

    private static string GlobalStatistics(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var competition = GetString(args, "competition");
        var season = GetInt(args, "season");
        var stats = service.GetGlobalStatistics(competition, season);
        return $"Matches: {stats.Matches}\nTotal goals: {stats.Goals}\nAverage goals per match: {stats.AverageGoalsPerMatch:F2}\nHome win rate: {stats.HomeWinRate:P1}\nDraw rate: {stats.DrawRate:P1}\nAway win rate: {stats.AwayWinRate:P1}";
    }

    private static string FindPlayers(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var name = GetString(args, "name");
        var nationality = GetString(args, "nationality");
        var club = GetString(args, "club");
        var position = GetString(args, "position");
        var minOverall = GetInt(args, "minOverall");
        var limit = GetInt(args, "limit") ?? 50;
        var players = service.FindPlayers(name, nationality, club, position, minOverall, limit);
        return FormatPlayers(players);
    }

    private static string TopPlayers(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var nationality = GetString(args, "nationality");
        var club = GetString(args, "club");
        var position = GetString(args, "position");
        var limit = GetInt(args, "limit") ?? 10;
        var players = service.GetTopPlayers(nationality, club, position, limit);
        return FormatPlayers(players);
    }

    private static string CompetitionsForTeam(SoccerQueryService service, IDictionary<string, JsonElement> args)
    {
        var team = GetString(args, "team");
        if (string.IsNullOrWhiteSpace(team))
            return "Error: team is required.";
        var normalized = NameNormalizer.Normalize(team);
        var competitions = service.Store.Matches
            .Where(m => m.InvolvesTeam(normalized))
            .Select(m => m.Competition)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(c => c)
            .ToList();
        if (competitions.Count == 0)
            return $"No competitions found for {team}.";
        return $"{team} has played in:\n" + string.Join("\n", competitions.Select(c => $"- {c}"));
    }

    private static string FormatMatches(IReadOnlyList<Match> matches)
    {
        if (matches.Count == 0)
            return "No matches found.";
        return string.Join("\n", matches.Select(m =>
            $"- {m.Date:yyyy-MM-dd}: {m.FormatScore()} ({m.Competition}{(!string.IsNullOrWhiteSpace(m.Round) ? $" Round {m.Round}" : "")}{(!string.IsNullOrWhiteSpace(m.Stage) ? $" {m.Stage}" : "")})"));
    }

    private static string FormatTeamStatistics(TeamStatistics stats)
    {
        return $"{stats.Context}:\n" +
               $"- Matches: {stats.Matches}\n" +
               $"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}\n" +
               $"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}\n" +
               $"- Win rate: {stats.WinRate:P1}\n" +
               $"- Home: {stats.HomeWins}W/{stats.HomeDraws}D/{stats.HomeLosses}L\n" +
               $"- Away: {stats.AwayWins}W/{stats.AwayDraws}D/{stats.AwayLosses}L";
    }

    private static string FormatPlayers(IReadOnlyList<Player> players)
    {
        if (players.Count == 0)
            return "No players found.";
        return string.Join("\n", players.Select((p, i) =>
            $"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}, Nationality: {p.Nationality}"));
    }

    private static string? GetString(IDictionary<string, JsonElement> args, string key)
    {
        if (args.TryGetValue(key, out var element) && element.ValueKind == JsonValueKind.String)
            return element.GetString();
        return null;
    }

    private static int? GetInt(IDictionary<string, JsonElement> args, string key)
    {
        if (args.TryGetValue(key, out var element))
        {
            if (element.ValueKind == JsonValueKind.Number && element.TryGetInt32(out var i))
                return i;
            if (element.ValueKind == JsonValueKind.String && int.TryParse(element.GetString(), out var parsed))
                return parsed;
        }
        return null;
    }

    private static bool? GetBool(IDictionary<string, JsonElement> args, string key)
    {
        if (args.TryGetValue(key, out var element) && element.ValueKind == JsonValueKind.True)
            return true;
        if (args.TryGetValue(key, out var element2) && element2.ValueKind == JsonValueKind.False)
            return false;
        return null;
    }

    private static DateTime? GetDate(IDictionary<string, JsonElement> args, string key)
    {
        var s = GetString(args, key);
        if (DateTime.TryParse(s, out var d))
            return d;
        return null;
    }

    internal static string FindDataRoot(string start)
    {
        var dir = new DirectoryInfo(start);
        while (dir != null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "data", "kaggle")))
            {
                return dir.FullName;
            }
            if (File.Exists(Path.Combine(dir.FullName, "TASK.md")) ||
                File.Exists(Path.Combine(dir.FullName, "BrazilianSoccerMcpServer.sln")))
            {
                // If no data here, keep searching upward if possible
                var dataDir = Path.Combine(dir.FullName, "data", "kaggle");
                if (Directory.Exists(dataDir))
                    return dir.FullName;
            }
            dir = dir.Parent;
        }
        return start;
    }
}
