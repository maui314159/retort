// Context block
// File: Mcp/ToolRegistry.cs
// Purpose: Registry of MCP tools exposed by the Brazilian Soccer MCP server. Each tool
// carries a name, a human-readable description, a JSON-Schema input shape, and a handler
// that maps a JSON object of arguments to a text answer. The registry constructs all
// services from a shared SoccerDataStore so a single in-memory dataset backs every tool
// invocation. tools/list returns the JSON array of tool descriptors; tools/call dispatches
// by name. Argument parsing is defensive so missing or malformed inputs produce a clear
// error message instead of crashing the server.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Mcp;

/// <summary>Holds tool descriptors and dispatches tool calls.</summary>
public sealed class ToolRegistry
{
    private readonly SoccerDataStore _store;
    private readonly MatchService _matches;
    private readonly TeamService _teams;
    private readonly PlayerService _players;
    private readonly CompetitionService _competitions;
    private readonly StatisticsService _stats;
    private readonly ResponseFormatter _formatter = new();

    private readonly Dictionary<string, ToolEntry> _tools = new(StringComparer.Ordinal);

    public ToolRegistry(SoccerDataStore store)
    {
        _store = store;
        _matches = new MatchService(store);
        _teams = new TeamService(store, _matches);
        _players = new PlayerService(store);
        _competitions = new CompetitionService(store, _matches);
        _stats = new StatisticsService(store, _matches, _teams);
        Register();
    }

    /// <summary>Returns the JSON array of tool descriptors for tools/list.</summary>
    public JsonArray ListJson()
    {
        var arr = new JsonArray();
        foreach (var entry in _tools.Values)
        {
            arr.Add(entry.Descriptor);
        }
        return arr;
    }

    /// <summary>Invokes a tool by name with a JSON object of arguments.</summary>
    public string Invoke(string name, JsonNode arguments)
    {
        if (!_tools.TryGetValue(name, out var entry))
        {
            throw new ArgumentException($"Unknown tool: {name}");
        }
        var args = arguments as JsonObject ?? new JsonObject();
        return entry.Handler(args);
    }

    private void Register()
    {
        Add("search_matches", "Find matches by team, opponent, competition, season, and/or date range.",
            Schema(
                ("team", "string", "Team name (supports name variations)"),
                ("opponent", "string", "Opponent team name (optional)"),
                ("competition", "string", "One of: Brasileirao, CopaDoBrasil, Libertadores, BrFootballDataset, HistoricBrasileirao"),
                ("season", "integer", "Season year"),
                ("from_date", "string", "ISO date lower bound (yyyy-MM-dd)"),
                ("to_date", "string", "ISO date upper bound (yyyy-MM-dd)"),
                ("max", "integer", "Max matches to display")
            ),
            args =>
            {
                var matches = _matches.SearchMatches(
                    team: GetStr(args, "team"),
                    opponent: GetStr(args, "opponent"),
                    competition: ParseCompetition(GetStr(args, "competition")),
                    season: GetInt(args, "season"),
                    fromDate: ParseDate(GetStr(args, "from_date")),
                    toDate: ParseDate(GetStr(args, "to_date")));
                return _formatter.FormatMatches(matches, GetInt(args, "max") ?? 20);
            });

        Add("head_to_head", "Return the head-to-head record and recent matches between two teams.",
            Schema(
                ("team_a", "string", "First team"),
                ("team_b", "string", "Second team")
            ),
            args =>
            {
                var a = RequireStr(args, "team_a");
                var b = RequireStr(args, "team_b");
                return _formatter.FormatHeadToHead(_matches.HeadToHead(a, b));
            });

        Add("last_match_between", "Return the most recent match between two teams.",
            Schema(
                ("team_a", "string", "First team"),
                ("team_b", "string", "Second team")
            ),
            args =>
            {
                var a = RequireStr(args, "team_a");
                var b = RequireStr(args, "team_b");
                var m = _matches.LastMatchBetween(a, b);
                return m is null ? $"No matches found between {a} and {b}." : m.Summary;
            });

        Add("get_team_stats", "Return wins/losses/draws and goals for a team, optionally by season, competition, and venue.",
            Schema(
                ("team", "string", "Team name"),
                ("season", "integer", "Season year"),
                ("competition", "string", "Competition name"),
                ("venue", "string", "One of: All, Home, Away")
            ),
            args => _formatter.FormatTeamStats(_teams.GetTeamStats(
                RequireStr(args, "team"),
                GetInt(args, "season"),
                ParseCompetition(GetStr(args, "competition")),
                ParseVenue(GetStr(args, "venue")))));

        Add("compare_teams", "Compare two teams by full record plus head-to-head.",
            Schema(
                ("team_a", "string", "First team"),
                ("team_b", "string", "Second team"),
                ("season", "integer", "Season year"),
                ("competition", "string", "Competition name")
            ),
            args => _formatter.FormatComparison(_teams.CompareTeams(
                RequireStr(args, "team_a"),
                RequireStr(args, "team_b"),
                GetInt(args, "season"),
                ParseCompetition(GetStr(args, "competition")))));

        Add("search_players", "Search the FIFA player dataset by name, nationality, club, position, and minimum overall rating.",
            Schema(
                ("name", "string", "Player name substring"),
                ("nationality", "string", "Nationality (e.g. Brazil)"),
                ("club", "string", "Club name substring"),
                ("position", "string", "Position code (e.g. ST, LW, GK)"),
                ("min_overall", "integer", "Minimum overall rating"),
                ("top_n", "integer", "Max players to return")
            ),
            args =>
            {
                var players = _players.SearchPlayers(
                    name: GetStr(args, "name"),
                    nationality: GetStr(args, "nationality"),
                    club: GetStr(args, "club"),
                    position: GetStr(args, "position"),
                    minOverall: GetInt(args, "min_overall"),
                    topN: GetInt(args, "top_n") ?? 25);
                var title = BuildPlayersTitle(args);
                return _formatter.FormatPlayers(players, title);
            });

        Add("top_brazilian_players", "Return the highest-rated Brazilian players in the FIFA dataset.",
            Schema(
                ("top_n", "integer", "Max players to return")
            ),
            args =>
            {
                var n = GetInt(args, "top_n") ?? 10;
                var players = _players.SearchPlayers(nationality: "Brazil", topN: n);
                return _formatter.FormatPlayers(players, "Top-rated Brazilian players in dataset");
            });

        Add("brazilian_players_by_club", "Count Brazilian players per club, ordered by count.",
            Schema(
                ("top_n", "integer", "Max clubs to return")
            ),
            args =>
            {
                var n = GetInt(args, "top_n") ?? 25;
                var clubs = _players.BrazilianPlayersByClub(n);
                return _formatter.FormatClubCounts(clubs, "Brazilian players at clubs");
            });

        Add("get_standings", "Compute the Brasileirão standings for a season (top to bottom).",
            Schema(
                ("season", "integer", "Season year"),
                ("top_n", "integer", "Max rows to return")
            ),
            args =>
            {
                var season = RequireInt(args, "season");
                var n = GetInt(args, "top_n") ?? 50;
                return _formatter.FormatStandings(_competitions.GetBrasileiraoStandings(season, n), season);
            });

        Add("get_champion", "Return the computed Brasileirão champion for a season.",
            Schema(
                ("season", "integer", "Season year")
            ),
            args =>
            {
                var season = RequireInt(args, "season");
                var rows = _competitions.GetBrasileiraoStandings(season, 1);
                if (rows.Count == 0) return $"No standings available for season {season}.";
                var champ = rows[0];
                return $"{season} Brasileirao Champion: {champ.Team} ({champ.Points} pts)";
            });

        Add("get_average_goals", "Return the average goals per match for a competition/season.",
            Schema(
                ("competition", "string", "Competition name"),
                ("season", "integer", "Season year")
            ),
            args =>
            {
                var comp = ParseCompetition(GetStr(args, "competition"));
                var season = GetInt(args, "season");
                var avg = _stats.AverageGoalsPerMatch(comp, season);
                var label = comp is null ? "all competitions" : comp.ToString()!;
                var seasonLabel = season is null ? "" : $" {season}";
                return $"Average goals per match ({label}{seasonLabel}): {avg.ToString("0.00", CultureInfo.InvariantCulture)}";
            });

        Add("get_outcome_rates", "Return home win / draw / away win percentages for a competition/season.",
            Schema(
                ("competition", "string", "Competition name"),
                ("season", "integer", "Season year")
            ),
            args =>
            {
                var comp = ParseCompetition(GetStr(args, "competition"));
                var season = GetInt(args, "season");
                var rates = _stats.OutcomeRates(comp, season);
                return $"Outcome rates over {rates.MatchCount} matches: Home win {rates.HomeWinRate:0.0}%, Draw {rates.DrawRate:0.0}%, Away win {rates.AwayWinRate:0.0}%";
            });

        Add("get_biggest_wins", "Return the biggest victories by goal margin.",
            Schema(
                ("top_n", "integer", "Max matches to return"),
                ("competition", "string", "Competition name"),
                ("season", "integer", "Season year")
            ),
            args =>
            {
                var n = GetInt(args, "top_n") ?? 10;
                var comp = ParseCompetition(GetStr(args, "competition"));
                var season = GetInt(args, "season");
                var wins = _stats.BiggestWins(n, comp, season);
                var avg = _stats.AverageGoalsPerMatch(comp, season);
                var rates = _stats.OutcomeRates(comp, season);
                return _formatter.FormatBiggestWins(wins, avg, rates);
            });

        Add("best_away_record", "Return the team with the best away record for a season/competition.",
            Schema(
                ("season", "integer", "Season year"),
                ("competition", "string", "Competition name"),
                ("min_matches", "integer", "Minimum away matches required")
            ),
            args =>
            {
                var season = GetInt(args, "season");
                var comp = ParseCompetition(GetStr(args, "competition"));
                var min = GetInt(args, "min_matches") ?? 5;
                var best = _stats.BestAwayRecord(season, comp, min);
                return best is null ? "No team meets the minimum away match threshold." : _formatter.FormatTeamStats(best);
            });
    }

    private void Add(string name, string description, JsonObject schema, Func<JsonObject, string> handler)
    {
        _tools[name] = new ToolEntry(new JsonObject
        {
            ["name"] = name,
            ["description"] = description,
            ["inputSchema"] = schema,
        }, handler);
    }

    private static JsonObject Schema(params (string Name, string Type, string Description)[] fields)
    {
        var props = new JsonObject();
        var required = new JsonArray();
        foreach (var (n, t, d) in fields)
        {
            props[n] = new JsonObject
            {
                ["type"] = t,
                ["description"] = d,
            };
        }
        var schema = new JsonObject
        {
            ["type"] = "object",
            ["properties"] = props,
        };
        return schema;
    }

    private string BuildPlayersTitle(JsonObject args)
    {
        var parts = new List<string>();
        if (GetStr(args, "nationality") is { } nat) parts.Add(nat);
        if (GetStr(args, "club") is { } club) parts.Add(club);
        if (GetStr(args, "position") is { } pos) parts.Add(pos + "s");
        if (parts.Count == 0) return "Players in dataset";
        return string.Join(" at ", parts) + " (top by overall)";
    }

    private static string? GetStr(JsonObject args, string key)
    {
        if (args.TryGetPropertyValue(key, out var v) && v is not null)
        {
            var s = v.ToString();
            return string.IsNullOrWhiteSpace(s) ? null : s.Trim();
        }
        return null;
    }

    private static string RequireStr(JsonObject args, string key)
    {
        var v = GetStr(args, key) ?? throw new ArgumentException($"Missing required argument: {key}");
        return v;
    }

    private static int? GetInt(JsonObject args, string key)
    {
        if (args.TryGetPropertyValue(key, out var v) && v is not null)
        {
            if (v is JsonValue jv && jv.TryGetValue<int>(out var i)) return i;
            if (int.TryParse(v.ToString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)) return parsed;
        }
        return null;
    }

    private static int RequireInt(JsonObject args, string key)
    {
        var v = GetInt(args, key) ?? throw new ArgumentException($"Missing required integer argument: {key}");
        return v;
    }

    private static DateTime? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out var d)
            ? d
            : DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out d) ? d : (DateTime?)null;
    }

    private static Competition? ParseCompetition(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return Enum.TryParse<Competition>(s, ignoreCase: true, out var c) ? c : null;
    }

    private static Venue ParseVenue(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return Venue.All;
        return Enum.TryParse<Venue>(s, ignoreCase: true, out var v) ? v : Venue.All;
    }

    private sealed record ToolEntry(JsonObject Descriptor, Func<JsonObject, string> Handler);
}
