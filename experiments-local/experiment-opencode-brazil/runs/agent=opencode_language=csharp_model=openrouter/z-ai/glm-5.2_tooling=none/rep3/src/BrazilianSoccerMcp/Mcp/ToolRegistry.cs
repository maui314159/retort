using System.Globalization;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Mcp;

/// <summary>
/// Holds the catalogue of MCP tools exposed by this server. Each tool is a
/// name, JSON schema for its arguments, and a delegate that turns those
/// arguments into a text response (which the LLM host sees as the tool
/// result).
/// </summary>
public sealed class ToolRegistry
{
    private readonly MatchService _matches;
    private readonly TeamService _teams;
    private readonly PlayerService _players;
    private readonly CompetitionService _competitions;
    private readonly Dictionary<string, Tool> _byName;

    public ToolRegistry(MatchService matches, TeamService teams,
        PlayerService players, CompetitionService competitions)
    {
        _matches = matches;
        _teams = teams;
        _players = players;
        _competitions = competitions;

        _byName = new(StringComparer.OrdinalIgnoreCase);
        foreach (var t in BuildTools()) _byName[t.Name] = t;
    }

    public IEnumerable<Tool> Tools => _byName.Values;
    public Tool Get(string name) => _byName.TryGetValue(name, out var t)
        ? t
        : throw new ArgumentException($"Unknown tool: {name}");

    private IEnumerable<Tool> BuildTools()
    {
        yield return new Tool(
            "search_matches",
            "Search Brazilian soccer matches across all CSV datasets by team, opponent, competition, season and date range.",
            Schema(properties: new()
            {
                ["team"] = S("Team name (any spelling; normalized internally)."),
                ["opponent"] = S("Optional opponent name."),
                ["competition"] = S("Competition tag: Brasileirao, CopaDoBrasil, Libertadores, or substring."),
                ["season"] = S("Four-digit year, e.g. 2023."),
                ["from"] = S("Start date (ISO yyyy-MM-dd)."),
                ["to"] = S("End date (ISO yyyy-MM-dd)."),
            }),
            args =>
            {
                var matches = _matches.Search(
                    Str(args, "team"),
                    Str(args, "opponent"),
                    Str(args, "competition"),
                    Int(args, "season"),
                    Date(args, "from"),
                    Date(args, "to"));
                if (matches.Count == 0) return "No matches found for the given criteria.";
                var sb = new System.Text.StringBuilder();
                sb.AppendLine($"Found {matches.Count} matches:");
                foreach (var m in matches.Take(100)) sb.AppendLine(m.ToString());
                if (matches.Count > 100) sb.AppendLine($"... ({matches.Count - 100} more)");
                return sb.ToString().TrimEnd();
            });

        yield return new Tool(
            "head_to_head",
            "Compare two teams head-to-head: wins/draws/losses and the list of matches between them.",
            Schema(properties: new()
            {
                ["teamA"] = S("First team name."),
                ["teamB"] = S("Second team name."),
            }, required: new[] { "teamA", "teamB" }),
            args =>
            {
                var a = Str(args, "teamA");
                var b = Str(args, "teamB");
                if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b))
                    throw new ArgumentException("Both teamA and teamB are required.");
                var h2h = _matches.HeadToHead(a, b);
                var sb = new System.Text.StringBuilder();
                sb.AppendLine($"{a} vs {b} head-to-head:");
                sb.AppendLine($"- {a} wins: {h2h.WinsA}");
                sb.AppendLine($"- {b} wins: {h2h.WinsB}");
                sb.AppendLine($"- Draws: {h2h.Draws}");
                sb.AppendLine($"- Total matches in dataset: {h2h.Matches.Count}");
                foreach (var m in h2h.Matches.Take(50)) sb.AppendLine(m.ToString());
                return sb.ToString().TrimEnd();
            });

        yield return new Tool(
            "team_stats",
            "Aggregate win/draw/loss and goal statistics for a single team, optionally filtered by season, competition and venue (home/away).",
            Schema(properties: new()
            {
                ["team"] = S("Team name.", required: true),
                ["season"] = S("Four-digit year."),
                ["competition"] = S("Competition tag."),
                ["venue"] = S("\"home\" or \"away\"."),
            }, required: new[] { "team" }),
            args =>
            {
                var team = Str(args, "team") ?? throw new ArgumentException("team is required.");
                var stats = _teams.GetStats(team, Int(args, "season"), Str(args, "competition"), Str(args, "venue"));
                return FormatStats(stats);
            });

        yield return new Tool(
            "search_teams",
            "List team display names matching a name fragment (helps the LLM discover canonical spellings).",
            Schema(properties: new() { ["query"] = S("Name fragment.", required: true) },
                   required: new[] { "query" }),
            args =>
            {
                var q = Str(args, "query") ?? throw new ArgumentException("query is required.");
                var teams = _teams.SearchTeams(q);
                return teams.Count == 0 ? $"No teams match '{q}'." : string.Join("\n", teams);
            });

        yield return new Tool(
            "search_players",
            "Search the FIFA player database by name, nationality, club, position and minimum overall rating.",
            Schema(properties: new()
            {
                ["name"] = S("Player name fragment."),
                ["nationality"] = S("Country, e.g. Brazil."),
                ["club"] = S("Club name fragment."),
                ["position"] = S("Position code, e.g. ST, LW, GK."),
                ["minOverall"] = S("Minimum overall rating (0-99)."),
                ["limit"] = S("Max results (default 50)."),
            }),
            args =>
            {
                var players = _players.Search(
                    Str(args, "name"),
                    Str(args, "nationality"),
                    Str(args, "club"),
                    Str(args, "position"),
                    Int(args, "minOverall"),
                    Int(args, "limit") ?? 50);
                if (players.Count == 0) return "No players match the given criteria.";
                var sb = new System.Text.StringBuilder();
                foreach (var p in players) sb.AppendLine(p.ToString());
                return sb.ToString().TrimEnd();
            });

        yield return new Tool(
            "players_by_club",
            "Group players by club for a given filter (e.g. Brazilian players at Brazilian clubs).",
            Schema(properties: new()
            {
                ["nationality"] = S("Country filter, e.g. Brazil."),
                ["clubContains"] = S("Club name fragment, e.g. Flamengo."),
                ["limit"] = S("Max clubs returned (default 25)."),
            }),
            args =>
            {
                var groups = _players.GroupByClub(
                    Str(args, "nationality"),
                    Str(args, "clubContains"),
                    Int(args, "limit") ?? 25);
                if (groups.Count == 0) return "No clubs match the given criteria.";
                var sb = new System.Text.StringBuilder();
                foreach (var g in groups)
                    sb.AppendLine($"{g.Club}: {g.Count} players (avg overall {g.AverageOverall:0.#})");
                return sb.ToString().TrimEnd();
            });

        yield return new Tool(
            "standings",
            "Compute competition standings for a given season from match results (3 pts win, 1 pt draw).",
            Schema(properties: new()
            {
                ["competition"] = S("Competition tag, e.g. Brasileirao.", required: true),
                ["season"] = S("Four-digit year.", required: true),
            }, required: new[] { "competition", "season" }),
            args =>
            {
                var comp = Str(args, "competition") ?? throw new ArgumentException("competition is required.");
                var season = Int(args, "season") ?? throw new ArgumentException("season is required.");
                var table = _competitions.GetStandings(comp, season);
                var sb = new System.Text.StringBuilder();
                sb.AppendLine($"{season} {comp} standings ({table.Rows.Count} teams):");
                for (int i = 0; i < table.Rows.Count; i++)
                {
                    var r = table.Rows[i];
                    var label = i == 0 ? " - Champion" : "";
                    sb.AppendLine($"{r.Position}. {r.Team} - {r.Points} pts ({r.Wins}W {r.Draws}D {r.Losses}L) GF:{r.GoalsFor} GA:{r.GoalsAgainst}{label}");
                }
                return sb.ToString().TrimEnd();
            });

        yield return new Tool(
            "biggest_victories",
            "Return the largest-margin victories in the dataset, optionally filtered by competition and season.",
            Schema(properties: new()
            {
                ["competition"] = S("Competition tag."),
                ["season"] = S("Four-digit year."),
                ["limit"] = S("Max results (default 10)."),
            }),
            args =>
            {
                var list = _competitions.BiggestVictories(
                    Str(args, "competition"),
                    Int(args, "season"),
                    Int(args, "limit") ?? 10);
                if (list.Count == 0) return "No victories match the given criteria.";
                var sb = new System.Text.StringBuilder();
                for (int i = 0; i < list.Count; i++)
                    sb.AppendLine($"{i + 1}. {list[i]}");
                return sb.ToString().TrimEnd();
            });

        yield return new Tool(
            "match_averages",
            "Average goals per match and home/away/draw win rates for a competition (optionally a single season).",
            Schema(properties: new()
            {
                ["competition"] = S("Competition tag."),
                ["season"] = S("Four-digit year."),
            }),
            args =>
            {
                var avg = _competitions.GetAverages(Str(args, "competition"), Int(args, "season"));
                return $"Matches: {avg.Matches}\nAverage goals per match: {avg.AverageGoals:0.##}\n"
                     + $"Home win rate: {avg.HomeWinPercent:0.#}%\nAway win rate: {avg.AwayWinPercent:0.#}%\nDraw rate: {avg.DrawPercent:0.#}%";
            });

        yield return new Tool(
            "seasons",
            "List seasons available in the dataset for a competition.",
            Schema(properties: new() { ["competition"] = S("Competition tag.", required: true) },
                   required: new[] { "competition" }),
            args =>
            {
                var comp = Str(args, "competition") ?? throw new ArgumentException("competition is required.");
                var seasons = _competitions.GetSeasons(comp);
                return seasons.Count == 0
                    ? $"No seasons found for {comp}."
                    : string.Join(", ", seasons);
            });
    }

    private static string FormatStats(TeamStats s)
    {
        var venue = string.IsNullOrEmpty(s.Venue) ? "all" : s.Venue;
        var season = s.Season.HasValue ? s.Season.Value.ToString() : "all";
        var comp = string.IsNullOrEmpty(s.Competition) ? "all" : s.Competition;
        return $"{s.Team} record ({season} {comp}, venue: {venue}):\n"
             + $"- Matches: {s.Matches}\n"
             + $"- Wins: {s.Wins}, Draws: {s.Draws}, Losses: {s.Losses}\n"
             + $"- Goals For: {s.GoalsFor}, Goals Against: {s.GoalsAgainst}\n"
             + $"- Home matches: {s.HomeMatches}, Away matches: {s.AwayMatches}\n"
             + $"- Win rate: {s.WinRatePercent:0.#}%";
    }

    // ----- JSON schema helpers -----

    private static JsonObject S(string description, bool required = false)
    {
        var o = new JsonObject { ["type"] = "string", ["description"] = description };
        return o;
    }

    private static JsonObject Schema(Dictionary<string, JsonObject> properties, string[]? required = null)
    {
        var props = new JsonObject();
        foreach (var kv in properties) props[kv.Key] = kv.Value;
        var o = new JsonObject
        {
            ["type"] = "object",
            ["properties"] = props,
        };
        if (required != null && required.Length > 0)
        {
            var arr = new JsonArray();
            foreach (var r in required) arr.Add(r);
            o["required"] = arr;
        }
        return o;
    }

    // ----- argument extraction helpers -----

    private static string? Str(JsonObject args, string key)
        => args.TryGetPropertyValue(key, out var v) && v != null ? v.GetValue<string>() : null;

    private static int? Int(JsonObject args, string key)
    {
        if (!args.TryGetPropertyValue(key, out var v) || v == null) return null;
        if (v is JsonValue jv && jv.TryGetValue<int>(out var i)) return i;
        if (v is JsonValue jv2 && jv2.TryGetValue<long>(out var l)) return (int)l;
        var s = v.GetValue<string>();
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)) return parsed;
        return null;
    }

    private static DateTime? Date(JsonObject args, string key)
    {
        if (!args.TryGetPropertyValue(key, out var v) || v == null) return null;
        var s = v.GetValue<string>();
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal, out var d) ? d : DateTime.TryParse(s, out var d2) ? d2 : null;
    }
}

/// <summary>A single MCP tool: name, schema and a delegate that produces the text result.</summary>
public sealed record Tool(
    string Name,
    string Description,
    JsonObject InputSchema,
    Func<JsonObject, string> Invoke);
