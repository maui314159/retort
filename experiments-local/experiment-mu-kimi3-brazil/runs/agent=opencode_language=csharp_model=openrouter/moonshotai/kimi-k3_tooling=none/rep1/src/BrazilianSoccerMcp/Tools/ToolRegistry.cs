using System.Globalization;
using System.Text;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// Registers the MCP tools exposed by the server and formats their answers
/// following the layouts suggested by the specification.
/// </summary>
public sealed class ToolRegistry
{
    public sealed record ToolDefinition(string Name, string Description, JsonObject InputSchema, Func<JsonObject?, string> Handler)
    {
        public JsonObject ToMcpSchema() =>
            new()
            {
                ["name"] = Name,
                ["description"] = Description,
                ["inputSchema"] = InputSchema.DeepClone(),
            };
    }

    private readonly List<ToolDefinition> _tools;
    public IReadOnlyList<ToolDefinition> Tools => _tools;

    public ToolRegistry(SoccerDataService service)
    {
        _tools =
        [
            new ToolDefinition(
                "find_matches",
                "Find soccer matches filtered by team (either side), opponent, competition " +
                "(Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), season, date range " +
                "or round/stage. Examples: 'Flamengo vs Fluminense', 'Palmeiras matches in 2021', " +
                "'Copa do Brasil finals' (competition='Copa do Brasil', round='Final').",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "team":        { "type": "string", "description": "Team name (any spelling: 'Flamengo', 'Flamengo-RJ', ...)" },
                    "opponent":    { "type": "string", "description": "Opponent team name, for head-to-head style listings" },
                    "competition": { "type": "string", "description": "e.g. 'Brasileirão', 'Serie A', 'Copa do Brasil', 'Libertadores'" },
                    "season":      { "type": "integer", "description": "Season year, e.g. 2021" },
                    "date_from":   { "type": "string", "description": "ISO date yyyy-MM-dd (inclusive)" },
                    "date_to":     { "type": "string", "description": "ISO date yyyy-MM-dd (inclusive)" },
                    "round":       { "type": "string", "description": "Round/stage filter, e.g. 'Final', 'Round 22', 'Semifinals', 'Group stage'" },
                    "limit":       { "type": "integer", "description": "Max matches to return (default 25, max 500)", "default": 25 }
                  }
                }
                """),
                args => HandleFindMatches(service, args)),

            new ToolDefinition(
                "head_to_head",
                "Compare two teams head-to-head: recent meetings plus all-time wins/draws " +
                "summary across every loaded dataset.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "team1": { "type": "string", "description": "First team name" },
                    "team2": { "type": "string", "description": "Second team name" },
                    "limit": { "type": "integer", "description": "Max past meetings to list (default 15)", "default": 15 }
                  },
                  "required": ["team1", "team2"]
                }
                """),
                args => HandleHeadToHead(service, args)),

            new ToolDefinition(
                "team_statistics",
                "Win/draw/loss record, goals for/against and win rate for a team, optionally " +
                "filtered by season, competition and venue (home/away/all).",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "team":        { "type": "string", "description": "Team name" },
                    "season":      { "type": "integer", "description": "Season year (optional)" },
                    "competition": { "type": "string", "description": "Competition filter (optional)" },
                    "venue":       { "type": "string", "enum": ["all", "home", "away"], "description": "Match venue filter (default 'all')", "default": "all" }
                  },
                  "required": ["team"]
                }
                """),
                args => HandleTeamStatistics(service, args)),

            new ToolDefinition(
                "team_competitions",
                "List every competition a team has played in across the loaded datasets.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "team": { "type": "string", "description": "Team name" }
                  },
                  "required": ["team"]
                }
                """),
                args => HandleTeamCompetitions(service, args)),

            new ToolDefinition(
                "season_standings",
                "Compute a league table (points, W/D/L, goals) for a competition and season " +
                "from match results. Marks the champion and the relegation zone (bottom 4). " +
                "Brasileirão tables use a single data source per season to avoid double counting.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "competition": { "type": "string", "description": "e.g. 'Brasileirão' / 'Serie A' (default), also 'Serie B', 'Serie C'" },
                    "season":      { "type": "integer", "description": "Season year, e.g. 2019" }
                  },
                  "required": ["season"]
                }
                """),
                args => HandleSeasonStandings(service, args)),

            new ToolDefinition(
                "search_players",
                "Search the FIFA player database by (partial) name, nationality, club, " +
                "position code (e.g. 'ST', 'LW', 'GK') and minimum overall rating.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "name":        { "type": "string", "description": "Partial player name, e.g. 'Gabriel Barbosa' or 'Neymar'" },
                    "nationality": { "type": "string", "description": "e.g. 'Brazil', 'Argentina'" },
                    "club":        { "type": "string", "description": "Partial club name, e.g. 'Flamengo'" },
                    "position":    { "type": "string", "description": "Position code, e.g. 'ST', 'LW', 'CDM', 'GK'" },
                    "min_overall": { "type": "integer", "description": "Minimum FIFA overall rating" },
                    "limit":       { "type": "integer", "description": "Max results (default 15)", "default": 15 }
                  }
                }
                """),
                args => HandleSearchPlayers(service, args)),

            new ToolDefinition(
                "top_players",
                "Highest-rated players in the FIFA database, optionally filtered by " +
                "nationality (e.g. 'Brazil'), club and/or position.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "nationality": { "type": "string", "description": "e.g. 'Brazil'" },
                    "club":        { "type": "string", "description": "Partial club name" },
                    "position":    { "type": "string", "description": "Position code" },
                    "limit":       { "type": "integer", "description": "How many to return (default 10)", "default": 10 }
                  }
                }
                """),
                args => HandleTopPlayers(service, args)),

            new ToolDefinition(
                "match_statistics",
                "Aggregate match statistics: matches played, average goals per match, " +
                "home/draw/away win rates and the biggest victories. Optionally filtered " +
                "by competition and season.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "competition": { "type": "string", "description": "Competition filter (optional)" },
                    "season":      { "type": "integer", "description": "Season filter (optional)" },
                    "biggest_wins": { "type": "integer", "description": "How many biggest wins to list (default 5)", "default": 5 }
                  }
                }
                """),
                args => HandleMatchStatistics(service, args)),

            new ToolDefinition(
                "biggest_wins",
                "List the largest-margin victories in the datasets, optionally filtered " +
                "by competition and/or season.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "competition": { "type": "string", "description": "Competition filter (optional)" },
                    "season":      { "type": "integer", "description": "Season filter (optional)" },
                    "limit":       { "type": "integer", "description": "How many to return (default 10)", "default": 10 }
                  }
                }
                """),
                args => HandleBiggestWins(service, args)),

            new ToolDefinition(
                "find_derbies",
                "Find matches between traditional Brazilian rivals (Fla-Flu, Derby Paulista, " +
                "Gre-Nal, Majestoso, ...), optionally filtered by season.",
                Schema("""
                {
                  "type": "object",
                  "properties": {
                    "season": { "type": "integer", "description": "Season filter (optional)" },
                    "limit":  { "type": "integer", "description": "Max matches to return (default 25)", "default": 25 }
                  }
                }
                """),
                args => HandleFindDerbies(service, args)),

            new ToolDefinition(
                "list_datasets",
                "List the loaded CSV datasets with row counts and the distinct teams/seasons covered.",
                Schema("""{ "type": "object", "properties": {} }"""),
                _ => HandleListDatasets(service)),
        ];
    }

    // ---------- MCP plumbing ----------

    public JsonObject ListTools()
    {
        var array = new JsonArray();
        foreach (var tool in _tools)
            array.Add(tool.ToMcpSchema());
        return new JsonObject { ["tools"] = array };
    }

    public JsonObject CallTool(JsonObject? parameters)
    {
        var name = parameters?["name"]?.GetValue<string>()
            ?? throw new ToolCallException("tools/call requires a 'name' parameter");
        var tool = _tools.FirstOrDefault(t => t.Name == name)
            ?? throw new ToolCallException($"Unknown tool: {name}", JsonRpc.InvalidParams);
        var arguments = parameters?["arguments"] as JsonObject ?? new JsonObject();

        string text;
        var isError = false;
        try
        {
            text = tool.Handler(arguments);
        }
        catch (TeamResolutionException ex)
        {
            text = ex.Message;
            isError = true;
        }
        catch (ArgumentException ex)
        {
            text = ex.Message;
            isError = true;
        }

        return new JsonObject
        {
            ["content"] = new JsonArray(new JsonObject { ["type"] = "text", ["text"] = text }),
            ["isError"] = isError,
        };
    }

    private static JsonObject Schema(string json) =>
        JsonNode.Parse(json) as JsonObject ?? throw new InvalidOperationException("Bad tool schema JSON");

    // ---------- Argument helpers ----------

    private static string? GetString(JsonObject? args, string name) =>
        args?[name]?.GetValue<string>();

    private static int? GetInt(JsonObject? args, string name)
    {
        var node = args?[name];
        if (node is null) return null;
        if (node is JsonValue value)
        {
            if (value.TryGetValue<int>(out var i)) return i;
            if (value.TryGetValue<string>(out var s) &&
                int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out i)) return i;
        }
        throw new ArgumentException($"Parameter '{name}' must be an integer.");
    }

    private static int GetLimit(JsonObject? args, string name, int fallback) =>
        GetInt(args, name) is { } v ? Math.Clamp(v, 1, 500) : fallback;

    private static DateOnly? GetDate(JsonObject? args, string name)
    {
        var s = GetString(args, name);
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (DateOnly.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
            return d;
        throw new ArgumentException($"Parameter '{name}' must be an ISO date (yyyy-MM-dd), got '{s}'.");
    }

    // ---------- Tool handlers / answer formatting ----------

    private static string HandleFindMatches(SoccerDataService service, JsonObject? args)
    {
        var filter = new SoccerDataService.MatchFilter
        {
            Team = GetString(args, "team"),
            Opponent = GetString(args, "opponent"),
            Competition = GetString(args, "competition"),
            Season = GetInt(args, "season"),
            From = GetDate(args, "date_from"),
            To = GetDate(args, "date_to"),
            Round = GetString(args, "round"),
            Limit = GetLimit(args, "limit", 25),
        };

        var matches = service.FindMatches(filter);
        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        var title = BuildFilterTitle(service, filter);
        sb.AppendLine(title);
        foreach (var m in matches)
            sb.AppendLine($"- {m.Describe()}");
        return sb.ToString().TrimEnd();
    }

    private static string BuildFilterTitle(SoccerDataService service, SoccerDataService.MatchFilter filter)
    {
        var parts = new List<string>();
        if (filter.Team is not null && filter.Opponent is not null)
            parts.Add($"{service.ResolveTeam(filter.Team)} vs {service.ResolveTeam(filter.Opponent)}");
        else if (filter.Team is not null)
            parts.Add($"Matches involving {service.ResolveTeam(filter.Team)}");
        else if (filter.Opponent is not null)
            parts.Add($"Matches involving {service.ResolveTeam(filter.Opponent)}");
        else
            parts.Add("Matches");
        if (filter.Competition is not null)
            parts.Add($"in {SoccerDataService.ResolveCompetition(filter.Competition) ?? filter.Competition}");
        if (filter.Season is { } s) parts.Add($"season {s}");
        if (filter.Round is not null) parts.Add($"({filter.Round})");
        return string.Join(' ', parts) + ":";
    }

    private static string HandleHeadToHead(SoccerDataService service, JsonObject? args)
    {
        var team1 = GetString(args, "team1") ?? throw new ArgumentException("Parameter 'team1' is required.");
        var team2 = GetString(args, "team2") ?? throw new ArgumentException("Parameter 'team2' is required.");
        var limit = GetLimit(args, "limit", 15);

        var h2h = service.HeadToHead(team1, team2, limit);
        var sb = new StringBuilder();
        var derby = SoccerDataService.Derbies.FirstOrDefault(d =>
            (d.Value.Team1 == h2h.Team1 && d.Value.Team2 == h2h.Team2) ||
            (d.Value.Team1 == h2h.Team2 && d.Value.Team2 == h2h.Team1));
        sb.AppendLine(derby.Key is not null
            ? $"{h2h.Team1} vs {h2h.Team2} ({derby.Key} derby):"
            : $"{h2h.Team1} vs {h2h.Team2}:");
        if (h2h.Matches.Count == 0)
        {
            sb.AppendLine("No meetings found in the datasets.");
        }
        else
        {
            foreach (var m in h2h.Matches)
                sb.AppendLine($"- {m.Describe()}");
        }
        sb.AppendLine();
        sb.AppendLine($"Head-to-head in dataset: {h2h.Team1} {h2h.Team1Wins} wins, " +
                      $"{h2h.Team2} {h2h.Team2Wins} wins, {h2h.Draws} draws");
        return sb.ToString().TrimEnd();
    }

    private static string HandleTeamStatistics(SoccerDataService service, JsonObject? args)
    {
        var team = GetString(args, "team") ?? throw new ArgumentException("Parameter 'team' is required.");
        var season = GetInt(args, "season");
        var competition = GetString(args, "competition");
        var venue = (GetString(args, "venue") ?? "all").ToLowerInvariant() switch
        {
            "home" => SoccerDataService.Venue.Home,
            "away" => SoccerDataService.Venue.Away,
            _ => SoccerDataService.Venue.All,
        };

        var stats = service.GetTeamStatistics(team, season, competition, venue);
        var scope = new List<string>();
        if (season is { } s) scope.Add(s.ToString(CultureInfo.InvariantCulture));
        if (competition is not null) scope.Add(SoccerDataService.ResolveCompetition(competition) ?? competition);
        if (venue != SoccerDataService.Venue.All) scope.Add(venue == SoccerDataService.Venue.Home ? "home" : "away");
        var scopeText = scope.Count > 0 ? $" ({string.Join(", ", scope)})" : "";

        var sb = new StringBuilder();
        sb.AppendLine($"{stats.Team}{scopeText}:");
        sb.AppendLine($"- Matches: {stats.Matches}");
        sb.AppendLine($"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {stats.WinRate:F1}%");
        return sb.ToString().TrimEnd();
    }

    private static string HandleTeamCompetitions(SoccerDataService service, JsonObject? args)
    {
        var team = GetString(args, "team") ?? throw new ArgumentException("Parameter 'team' is required.");
        var competitions = service.TeamCompetitions(team);
        var canonical = service.ResolveTeam(team);
        var sb = new StringBuilder();
        sb.AppendLine($"{canonical} has played in:");
        foreach (var c in competitions)
            sb.AppendLine($"- {c}");
        return sb.ToString().TrimEnd();
    }

    private static string HandleSeasonStandings(SoccerDataService service, JsonObject? args)
    {
        var season = GetInt(args, "season") ?? throw new ArgumentException("Parameter 'season' is required.");
        var competition = GetString(args, "competition") ?? "Brasileirão Série A";

        var standings = service.GetStandings(competition, season);
        if (standings.Rows.Count == 0)
            return $"No played matches found for {standings.Competition} {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{season} {standings.Competition} standings (calculated from matches, {standings.SourceNote}):");
        foreach (var row in standings.Rows)
        {
            var tag = row.Position == 1 ? " - Champion"
                : standings.Rows.Count >= 8 && row.Position > standings.Rows.Count - 4 ? " - Relegated"
                : "";
            sb.AppendLine($"{row.Position}. {row.Team} - {row.Points} pts " +
                          $"({row.Wins}W, {row.Draws}D, {row.Losses}L, " +
                          $"GF {row.GoalsFor}, GA {row.GoalsAgainst}){tag}");
        }
        return sb.ToString().TrimEnd();
    }

    private static string HandleSearchPlayers(SoccerDataService service, JsonObject? args)
    {
        var filter = new SoccerDataService.PlayerFilter
        {
            Name = GetString(args, "name"),
            Nationality = GetString(args, "nationality"),
            Club = GetString(args, "club"),
            Position = GetString(args, "position"),
            MinOverall = GetInt(args, "min_overall"),
            Limit = GetLimit(args, "limit", 15),
        };

        var players = service.SearchPlayers(filter);
        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Players matching the criteria (top {players.Count} by overall rating):");
        var rank = 1;
        foreach (var p in players)
            sb.AppendLine($"{rank++}. {p.Describe()}");
        return sb.ToString().TrimEnd();
    }

    private static string HandleTopPlayers(SoccerDataService service, JsonObject? args)
    {
        var nationality = GetString(args, "nationality");
        var club = GetString(args, "club");
        var position = GetString(args, "position");
        var limit = GetLimit(args, "limit", 10);

        var players = service.TopPlayers(nationality, club, position, limit);
        if (players.Count == 0)
            return "No players found for the given criteria.";

        var scopeParts = new List<string>();
        if (position is not null) scopeParts.Add($"position {position}");
        if (nationality is not null) scopeParts.Add($"from {nationality}");
        if (club is not null) scopeParts.Add($"at clubs matching '{club}'");
        var scope = scopeParts.Count > 0 ? $" ({string.Join(", ", scopeParts)})" : "";

        var sb = new StringBuilder();
        sb.AppendLine($"Top-rated players{scope}:");
        var rank = 1;
        foreach (var p in players)
            sb.AppendLine($"{rank++}. {p.Describe()}");
        return sb.ToString().TrimEnd();
    }

    private static string HandleMatchStatistics(SoccerDataService service, JsonObject? args)
    {
        var competition = GetString(args, "competition");
        var season = GetInt(args, "season");
        var biggestWins = GetLimit(args, "biggest_wins", 5);

        var stats = service.GetMatchStatistics(competition, season, biggestWins);
        var scopeParts = new List<string>();
        if (competition is not null) scopeParts.Add(SoccerDataService.ResolveCompetition(competition) ?? competition);
        if (season is { } s) scopeParts.Add(s.ToString(CultureInfo.InvariantCulture));
        var scope = scopeParts.Count > 0 ? $" ({string.Join(", ", scopeParts)})" : " (all provided data)";

        var sb = new StringBuilder();
        sb.AppendLine($"Match statistics{scope}:");
        sb.AppendLine($"- Matches in dataset: {stats.TotalMatches} ({stats.PlayedMatches} with recorded scores)");
        sb.AppendLine($"- Average goals per match: {stats.AvgGoalsPerMatch:F2}");
        sb.AppendLine($"- Home win rate: {stats.HomeWinRate:F1}%");
        sb.AppendLine($"- Draw rate: {stats.DrawRate:F1}%");
        sb.AppendLine($"- Away win rate: {stats.AwayWinRate:F1}%");
        if (stats.BiggestWins.Count > 0)
        {
            sb.AppendLine();
            sb.AppendLine("Biggest victories:");
            var rank = 1;
            foreach (var m in stats.BiggestWins)
                sb.AppendLine($"{rank++}. {m.Describe()}");
        }
        return sb.ToString().TrimEnd();
    }

    private static string HandleBiggestWins(SoccerDataService service, JsonObject? args)
    {
        var competition = GetString(args, "competition");
        var season = GetInt(args, "season");
        var limit = GetLimit(args, "limit", 10);

        var wins = service.BiggestWins(competition, season, limit);
        if (wins.Count == 0)
            return "No matches found for the given criteria.";

        var scopeParts = new List<string>();
        if (competition is not null) scopeParts.Add(SoccerDataService.ResolveCompetition(competition) ?? competition);
        if (season is { } s) scopeParts.Add(s.ToString(CultureInfo.InvariantCulture));
        var scope = scopeParts.Count > 0 ? $" ({string.Join(", ", scopeParts)})" : " (all provided data)";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest victories{scope}:");
        var rank = 1;
        foreach (var m in wins)
            sb.AppendLine($"{rank++}. {m.Describe()}");
        return sb.ToString().TrimEnd();
    }

    private static string HandleFindDerbies(SoccerDataService service, JsonObject? args)
    {
        var season = GetInt(args, "season");
        var limit = GetLimit(args, "limit", 25);

        var derbies = service.FindDerbies(season, limit);
        if (derbies.Count == 0)
            return season is { } s
                ? $"No derby matches found for season {s}."
                : "No derby matches found in the datasets.";

        var sb = new StringBuilder();
        sb.AppendLine(season is { } s2 ? $"Derby matches in {s2}:" : "Derby matches (most recent):");
        foreach (var d in derbies)
            sb.AppendLine($"- [{d.DerbyName}] {d.Match.Describe()}");
        return sb.ToString().TrimEnd();
    }

    private static string HandleListDatasets(SoccerDataService service)
    {
        var sb = new StringBuilder();
        sb.AppendLine("Loaded datasets:");
        foreach (var d in service.Datasets)
            sb.AppendLine($"- {d.File}: {d.RowCount} rows ({d.Contents})");
        sb.AppendLine();
        sb.AppendLine($"Distinct teams: {service.Teams.Count}");
        sb.AppendLine($"Sample team names: {string.Join(", ", service.Teams.Take(10))}, ...");
        return sb.ToString().TrimEnd();
    }
}
