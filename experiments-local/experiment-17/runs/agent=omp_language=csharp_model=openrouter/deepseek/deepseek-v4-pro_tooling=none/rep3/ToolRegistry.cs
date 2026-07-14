using System.Text;
using System.Text.Json;
using BrazilianSoccerMCP.Models;
using BrazilianSoccerMCP.Services;

namespace BrazilianSoccerMCP;

/// <summary>
/// Registry of all MCP tools and their execution logic.
/// </summary>
public class ToolRegistry
{
    private readonly MatchService _matchService;
    private readonly PlayerService _playerService;
    private readonly CompetitionService _competitionService;

    public ToolRegistry(MatchService matchService, PlayerService playerService, CompetitionService competitionService)
    {
        _matchService = matchService;
        _playerService = playerService;
        _competitionService = competitionService;
    }

    public List<ToolDefinition> GetToolDefinitions()
    {
        return new List<ToolDefinition>
        {
            new()
            {
                Name = "search_matches",
                Description = "Search for soccer matches by team, competition, season, date range, opponent, round, or stage. Returns matches ordered by date descending.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        team = new { type = "string", description = "Team name to search for (home or away)" },
                        opponent = new { type = "string", description = "Opponent team name" },
                        competition = new { type = "string", description = "Competition name (e.g., Brasileirão, Copa do Brasil, Copa Libertadores)" },
                        season = new { type = "integer", description = "Season year (e.g., 2023)" },
                        from_date = new { type = "string", description = "Start date in ISO format (e.g., 2023-01-01)" },
                        to_date = new { type = "string", description = "End date in ISO format" },
                        round = new { type = "string", description = "Match round (e.g., 1, final)" },
                        stage = new { type = "string", description = "Tournament stage (e.g., group stage, knockout)" },
                        limit = new { type = "integer", description = "Maximum results (default 200)" },
                    }
                })
            },
            new()
            {
                Name = "get_team_stats",
                Description = "Get comprehensive statistics for a team: wins, losses, draws, goals, home/away records.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        team = new { type = "string", description = "Team name" },
                        competition = new { type = "string", description = "Filter by competition (optional)" },
                        season = new { type = "integer", description = "Filter by season year (optional)" },
                    },
                    required = new[] { "team" }
                })
            },
            new()
            {
                Name = "head_to_head",
                Description = "Compare two teams head-to-head: match history, win/loss/draw record.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        team1 = new { type = "string", description = "First team name" },
                        team2 = new { type = "string", description = "Second team name" },
                    },
                    required = new[] { "team1", "team2" }
                })
            },
            new()
            {
                Name = "search_players",
                Description = "Search FIFA player database by name, nationality, club, position, rating, or age.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        name = new { type = "string", description = "Player name (partial match)" },
                        nationality = new { type = "string", description = "Nationality (e.g., Brazil, Argentina)" },
                        club = new { type = "string", description = "Club name (partial match)" },
                        position = new { type = "string", description = "Playing position (e.g., ST, LW, GK, CDM)" },
                        min_rating = new { type = "integer", description = "Minimum FIFA overall rating" },
                        max_rating = new { type = "integer", description = "Maximum FIFA overall rating" },
                        min_age = new { type = "integer", description = "Minimum age" },
                        max_age = new { type = "integer", description = "Maximum age" },
                        sort_by = new { type = "string", description = "Sort field: overall, potential, age, name" },
                        limit = new { type = "integer", description = "Maximum results (default 100)" },
                    }
                })
            },
            new()
            {
                Name = "get_player",
                Description = "Get detailed information about a specific player by name.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        name = new { type = "string", description = "Player name" },
                    },
                    required = new[] { "name" }
                })
            },
            new()
            {
                Name = "get_standings",
                Description = "Get league standings for a competition and season, calculated from match results.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        competition = new { type = "string", description = "Competition name (e.g., Brasileirão)" },
                        season = new { type = "integer", description = "Season year (e.g., 2023)" },
                    },
                    required = new[] { "competition", "season" }
                })
            },
            new()
            {
                Name = "get_biggest_wins",
                Description = "Get the biggest victories by goal difference in the dataset.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        competition = new { type = "string", description = "Filter by competition (optional)" },
                        limit = new { type = "integer", description = "Maximum results (default 20)" },
                    }
                })
            },
            new()
            {
                Name = "get_league_stats",
                Description = "Get aggregate league statistics: total matches, goals, home/away win rates, averages.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        competition = new { type = "string", description = "Competition name (optional)" },
                        season = new { type = "integer", description = "Season year (optional)" },
                    }
                })
            },
            new()
            {
                Name = "list_competitions",
                Description = "List all competitions available in the dataset.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new { }
                })
            },
            new()
            {
                Name = "list_teams",
                Description = "List all teams available in the dataset, optionally filtered by competition.",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        competition = new { type = "string", description = "Filter by competition (optional)" },
                    }
                })
            },
            new()
            {
                Name = "get_champion",
                Description = "Get the champion of a competition for a specific season (calculated from match results).",
                InputSchema = JsonSerializer.SerializeToElement(new
                {
                    type = "object",
                    properties = new
                    {
                        competition = new { type = "string", description = "Competition name (e.g., Brasileirão)" },
                        season = new { type = "integer", description = "Season year" },
                    },
                    required = new[] { "competition", "season" }
                })
            },
        };
    }

    public CallToolResult ExecuteTool(string name, JsonElement? arguments)
    {
        var result = new StringBuilder();

        try
        {
            switch (name)
            {
                case "search_matches":
                    result.Append(SearchMatches(arguments));
                    break;
                case "get_team_stats":
                    result.Append(GetTeamStats(arguments));
                    break;
                case "head_to_head":
                    result.Append(HeadToHead(arguments));
                    break;
                case "search_players":
                    result.Append(SearchPlayers(arguments));
                    break;
                case "get_player":
                    result.Append(GetPlayer(arguments));
                    break;
                case "get_standings":
                    result.Append(GetStandings(arguments));
                    break;
                case "get_biggest_wins":
                    result.Append(GetBiggestWins(arguments));
                    break;
                case "get_league_stats":
                    result.Append(GetLeagueStats(arguments));
                    break;
                case "list_competitions":
                    result.Append(ListCompetitions());
                    break;
                case "list_teams":
                    result.Append(ListTeams(arguments));
                    break;
                case "get_champion":
                    result.Append(GetChampion(arguments));
                    break;
                default:
                    return new CallToolResult
                    {
                        Content = new List<ContentItem>
                        {
                            new() { Type = "text", Text = $"Unknown tool: {name}" }
                        }
                    };
            }
        }
        catch (Exception ex)
        {
            return new CallToolResult
            {
                Content = new List<ContentItem>
                {
                    new() { Type = "text", Text = $"Error executing {name}: {ex.Message}" }
                }
            };
        }

        return new CallToolResult
        {
            Content = new List<ContentItem>
            {
                new() { Type = "text", Text = result.ToString() }
            }
        };
    }

    // --- Tool implementations ---

    private string SearchMatches(JsonElement? args)
    {
        string? team = GetStringArg(args, "team");
        string? opponent = GetStringArg(args, "opponent");
        string? competition = GetStringArg(args, "competition");
        int? season = GetIntArg(args, "season");
        DateTime? fromDate = GetDateArg(args, "from_date");
        DateTime? toDate = GetDateArg(args, "to_date");
        string? round = GetStringArg(args, "round");
        string? stage = GetStringArg(args, "stage");
        int limit = GetIntArg(args, "limit") ?? 200;

        var matches = _matchService.SearchMatches(team, competition, season, fromDate, toDate, opponent, round, stage, limit);

        var sb = new StringBuilder();
        sb.AppendLine($"Found {matches.Count} match(es):");
        sb.AppendLine();

        foreach (var m in matches)
        {
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition}{(m.Round != null ? $" Round {m.Round}" : "")}{(m.Stage != null ? $" - {m.Stage}" : "")}{(m.Season.HasValue ? $" - {m.Season}" : "")})");
        }

        if (matches.Count == limit)
            sb.AppendLine($"\n(Results limited to {limit})");

        return sb.ToString();
    }

    private string GetTeamStats(JsonElement? args)
    {
        var team = GetStringArg(args, "team") ?? "";
        var competition = GetStringArg(args, "competition");
        var season = GetIntArg(args, "season");

        var stats = _matchService.GetTeamStats(team, competition, season);

        var sb = new StringBuilder();
        sb.AppendLine($"{stats.Team} Statistics{(stats.Competition != null ? $" - {stats.Competition}" : "")}{(stats.Season.HasValue ? $" {stats.Season}" : "")}:");
        sb.AppendLine();
        sb.AppendLine($"Overall Record:");
        sb.AppendLine($"  Matches: {stats.TotalMatches}");
        sb.AppendLine($"  Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"  Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}");
        sb.AppendLine($"  Goal Difference: {stats.GoalsFor - stats.GoalsAgainst}");
        sb.AppendLine($"  Win Rate: {stats.WinRate}%");
        sb.AppendLine();
        sb.AppendLine($"Home Record:");
        sb.AppendLine($"  Matches: {stats.HomeMatches}");
        sb.AppendLine($"  Wins: {stats.HomeWins}, Draws: {stats.HomeDraws}, Losses: {stats.HomeLosses}");
        sb.AppendLine($"  Goals For: {stats.HomeGoalsFor}, Goals Against: {stats.HomeGoalsAgainst}");
        sb.AppendLine();
        sb.AppendLine($"Away Record:");
        sb.AppendLine($"  Matches: {stats.AwayMatches}");
        sb.AppendLine($"  Wins: {stats.AwayWins}, Draws: {stats.AwayDraws}, Losses: {stats.AwayLosses}");
        sb.AppendLine($"  Goals For: {stats.AwayGoalsFor}, Goals Against: {stats.AwayGoalsAgainst}");

        return sb.ToString();
    }

    private string HeadToHead(JsonElement? args)
    {
        var team1 = GetStringArg(args, "team1") ?? "";
        var team2 = GetStringArg(args, "team2") ?? "";

        var h2h = _matchService.GetHeadToHead(team1, team2);

        var sb = new StringBuilder();
        sb.AppendLine($"{h2h.Team1} vs {h2h.Team2} Head-to-Head:");
        sb.AppendLine();
        sb.AppendLine($"Total Matches: {h2h.TotalMatches}");
        sb.AppendLine($"{h2h.Team1} Wins: {h2h.Team1Wins}");
        sb.AppendLine($"{h2h.Team2} Wins: {h2h.Team2Wins}");
        sb.AppendLine($"Draws: {h2h.Draws}");
        sb.AppendLine();

        if (h2h.Matches.Count > 0)
        {
            sb.AppendLine("Recent Matches:");
            foreach (var m in h2h.Matches.Take(20))
            {
                sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition}{(m.Season.HasValue ? $" {m.Season}" : "")})");
            }
            if (h2h.Matches.Count > 20)
                sb.AppendLine($"  ... and {h2h.Matches.Count - 20} more matches");
        }

        return sb.ToString();
    }

    private string SearchPlayers(JsonElement? args)
    {
        string? name = GetStringArg(args, "name");
        string? nationality = GetStringArg(args, "nationality");
        string? club = GetStringArg(args, "club");
        string? position = GetStringArg(args, "position");
        int? minRating = GetIntArg(args, "min_rating");
        int? maxRating = GetIntArg(args, "max_rating");
        int? minAge = GetIntArg(args, "min_age");
        int? maxAge = GetIntArg(args, "max_age");
        string? sortBy = GetStringArg(args, "sort_by");
        bool desc = GetStringArg(args, "order")?.ToLowerInvariant() != "asc";
        int limit = GetIntArg(args, "limit") ?? 100;

        var players = _playerService.SearchPlayers(name, nationality, club, position, minRating, maxRating, minAge, maxAge, sortBy, desc, limit);

        var sb = new StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s):");
        sb.AppendLine();

        foreach (var p in players)
        {
            sb.AppendLine($"- {p.Name} | Overall: {p.Overall} | Position: {p.Position} | Age: {p.Age} | Club: {p.Club} | Nationality: {p.Nationality}");
        }

        return sb.ToString();
    }

    private string GetPlayer(JsonElement? args)
    {
        var name = GetStringArg(args, "name");
        if (string.IsNullOrWhiteSpace(name))
            return "Player name is required.";

        var player = _playerService.GetPlayerByName(name);
        if (player == null)
            return $"Player '{name}' not found.";

        var sb = new StringBuilder();
        sb.AppendLine($"Player: {player.Name}");
        sb.AppendLine($"  Overall: {player.Overall} | Potential: {player.Potential}");
        sb.AppendLine($"  Age: {player.Age} | Nationality: {player.Nationality}");
        sb.AppendLine($"  Club: {player.Club}");
        sb.AppendLine($"  Position: {player.Position} | Jersey: {player.JerseyNumber}");
        sb.AppendLine($"  Height: {player.Height} | Weight: {player.Weight}");
        sb.AppendLine($"  Preferred Foot: {player.PreferredFoot} | Work Rate: {player.WorkRate}");
        sb.AppendLine();
        sb.AppendLine("Key Attributes:");
        sb.AppendLine($"  Pace: ACC {player.Acceleration} SPR {player.SprintSpeed}");
        sb.AppendLine($"  Shooting: FIN {player.Finishing} SHO {player.ShotPower} LON {player.LongShots} PEN {player.Penalties}");
        sb.AppendLine($"  Passing: SHO {player.ShortPassing} LON {player.LongPassing} CRO {player.Crossing} VIS {player.Vision}");
        sb.AppendLine($"  Dribbling: DRI {player.Dribbling} BAL {player.BallControl} AGI {player.Agility}");
        sb.AppendLine($"  Defense: DEF {player.StandingTackle} SLD {player.SlidingTackle} INT {player.Interceptions}");
        sb.AppendLine($"  Physical: STR {player.Strength} STA {player.Stamina} JUM {player.Jumping}");
        if (player.Position == "GK")
            sb.AppendLine($"  Goalkeeping: DIV {player.GKDiving} HAN {player.GKHandling} KIC {player.GKKicking} POS {player.GKPositioning} REF {player.GKReflexes}");

        return sb.ToString();
    }

    private string GetStandings(JsonElement? args)
    {
        var competition = GetStringArg(args, "competition") ?? "Brasileirão";
        var season = GetIntArg(args, "season") ?? 2023;

        var standings = _competitionService.GetStandings(competition, season);

        if (standings.Count == 0)
            return $"No standings found for {competition} {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} Standings:");
        sb.AppendLine();
        sb.AppendLine($"{"Pos",-4} {"Team",-25} {"P",-3} {"W",-3} {"D",-3} {"L",-3} {"GF",-4} {"GA",-4} {"GD",-4} {"Pts",-4}");
        sb.AppendLine(new string('-', 65));

        foreach (var s in standings)
        {
            sb.AppendLine($"{s.Position,-4} {s.Team,-25} {s.Played,-3} {s.Wins,-3} {s.Draws,-3} {s.Losses,-3} {s.GoalsFor,-4} {s.GoalsAgainst,-4} {s.GoalDifference,-4} {s.Points,-4}");
        }

        // Champion and relegation
        var champion = standings.FirstOrDefault();
        if (champion != null)
            sb.AppendLine($"\nChampion: {champion.Team} ({champion.Points} pts)");

        if (standings.Count >= 4)
        {
            sb.AppendLine($"Relegated: {string.Join(", ", standings.TakeLast(4).Select(s => s.Team))}");
        }

        return sb.ToString();
    }

    private string GetBiggestWins(JsonElement? args)
    {
        var competition = GetStringArg(args, "competition");
        int limit = GetIntArg(args, "limit") ?? 20;

        var matches = _matchService.GetBiggestWins(competition, limit);

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest Victories{(competition != null ? $" - {competition}" : "")}:");
        sb.AppendLine();

        for (int i = 0; i < matches.Count; i++)
        {
            var m = matches[i];
            sb.AppendLine($"{i + 1}. {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition}{(m.Season.HasValue ? $" {m.Season}" : "")})");
        }

        return sb.ToString();
    }

    private string GetLeagueStats(JsonElement? args)
    {
        var competition = GetStringArg(args, "competition");
        var season = GetIntArg(args, "season");

        var stats = _matchService.GetLeagueStats(competition, season);

        var sb = new StringBuilder();
        sb.AppendLine($"League Statistics{(competition != null ? $" - {competition}" : "")}{(season.HasValue ? $" {season}" : "")}:");
        sb.AppendLine();
        sb.AppendLine($"Total Matches: {stats.TotalMatches}");
        sb.AppendLine($"Total Goals: {stats.TotalGoals}");
        sb.AppendLine($"Average Goals per Match: {stats.AverageGoalsPerMatch}");
        sb.AppendLine();
        sb.AppendLine($"Home Wins: {stats.HomeWins} ({stats.HomeWinRate}%)");
        sb.AppendLine($"Away Wins: {stats.AwayWins} ({stats.AwayWinRate}%)");
        sb.AppendLine($"Draws: {stats.Draws} ({stats.DrawRate}%)");

        return sb.ToString();
    }

    private string ListCompetitions()
    {
        var competitions = _matchService.GetCompetitions();
        var sb = new StringBuilder();
        sb.AppendLine($"Available Competitions ({competitions.Count}):");
        sb.AppendLine();
        foreach (var c in competitions)
            sb.AppendLine($"- {c}");
        return sb.ToString();
    }

    private string ListTeams(JsonElement? args)
    {
        var competition = GetStringArg(args, "competition");
        var teams = _matchService.GetTeams(competition);

        var sb = new StringBuilder();
        sb.AppendLine($"Available Teams{(competition != null ? $" - {competition}" : "")} ({teams.Count}):");
        sb.AppendLine();
        foreach (var t in teams)
            sb.AppendLine($"- {t}");
        return sb.ToString();
    }

    private string GetChampion(JsonElement? args)
    {
        var competition = GetStringArg(args, "competition") ?? "Brasileirão";
        var season = GetIntArg(args, "season") ?? 2023;

        var champion = _competitionService.GetChampion(competition, season);
        if (champion == null)
            return $"No champion found for {competition} {season}.";

        return $"{competition} {season} Champion: {champion}";
    }

    // --- Argument helpers ---

    private static string? GetStringArg(JsonElement? args, string key)
    {
        if (args == null) return null;
        if (args.Value.TryGetProperty(key, out var prop) && prop.ValueKind == JsonValueKind.String)
            return prop.GetString();
        return null;
    }

    private static int? GetIntArg(JsonElement? args, string key)
    {
        if (args == null) return null;
        if (args.Value.TryGetProperty(key, out var prop))
        {
            if (prop.ValueKind == JsonValueKind.Number)
                return prop.GetInt32();
            if (prop.ValueKind == JsonValueKind.String && int.TryParse(prop.GetString(), out var v))
                return v;
        }
        return null;
    }

    private static DateTime? GetDateArg(JsonElement? args, string key)
    {
        if (args == null) return null;
        if (args.Value.TryGetProperty(key, out var prop) && prop.ValueKind == JsonValueKind.String)
        {
            if (DateTime.TryParse(prop.GetString(), out var dt))
                return dt;
        }
        return null;
    }
}
