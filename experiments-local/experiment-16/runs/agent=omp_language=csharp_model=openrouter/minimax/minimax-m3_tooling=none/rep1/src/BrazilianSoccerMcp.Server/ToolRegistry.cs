// =============================================================================
// Brazilian Soccer MCP Server
// File: ToolRegistry.cs
// Purpose: Catalogue of MCP tools exposed to the LLM and the glue that
//          dispatches a JSON arguments blob to the right QueryEngine
//          method, then formats the result as text.
// Context: Each tool has a name, a description (for the LLM), an
//          inputSchema (JSON Schema), and an Invoke method. To add a
//          new tool: append a record to the list in Build().
// =============================================================================

using System.Text.Json;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Server;

/// <summary>
/// One MCP tool: metadata + invoker.
/// </summary>
public sealed class Tool
{
    public required string Name { get; init; }
    public required string Description { get; init; }
    public required object InputSchema { get; init; }
    public required Func<JsonObject, JsonSerializerOptions, string> Invoke { get; init; }
}

/// <summary>
/// Registry of every tool the server exposes. The LLM sees these names in
/// the tools/list response and decides which to call for a given question.
/// </summary>
public sealed class ToolRegistry
{
    public static ToolRegistry Build(QueryEngine engine) => new(engine);

    private readonly List<Tool> _tools = new();
    private readonly Dictionary<string, Tool> _byName = new(StringComparer.Ordinal);

    private ToolRegistry(QueryEngine engine)
    {
        // -- Match queries --------------------------------------------------
        Register(new Tool
        {
            Name = "find_matches_by_team",
            Description = "Find matches involving a team. Returns up to 'limit' matches ordered by date desc. Optional season/competition filters.",
            InputSchema = Schema(
                ("team", "string", true, "Team name (with or without state suffix, e.g. 'Flamengo' or 'Flamengo-RJ')."),
                ("season", "integer", false, "Filter by season year, e.g. 2023."),
                ("competition", "string", false, "One of: Brasileirao, CopaDoBrasil, Libertadores, BrazilianExtended."),
                ("limit", "integer", false, "Max number of matches to return (default 50).")
            ),
            Invoke = (args, json) => InvokeFindMatchesByTeam(engine, args, json),
        });

        Register(new Tool
        {
            Name = "find_head_to_head",
            Description = "Find all head-to-head matches between two teams, ordered by date desc.",
            InputSchema = Schema(
                ("team_a", "string", true, "First team name."),
                ("team_b", "string", true, "Second team name."),
                ("limit", "integer", false, "Max number of matches to return (default 50).")
            ),
            Invoke = (args, json) => InvokeHeadToHead(engine, args, json),
        });

        Register(new Tool
        {
            Name = "last_match_between",
            Description = "Return the single most recent match between two teams, or null if none.",
            InputSchema = Schema(
                ("team_a", "string", true, "First team name."),
                ("team_b", "string", true, "Second team name.")
            ),
            Invoke = (args, json) => InvokeLastMatchBetween(engine, args, json),
        });

        // -- Team queries ---------------------------------------------------
        Register(new Tool
        {
            Name = "get_team_record",
            Description = "Win/loss/draw summary for one team. Optional season/competition/scope filters.",
            InputSchema = Schema(
                ("team", "string", true, "Team name."),
                ("season", "integer", false, "Filter by season year."),
                ("competition", "string", false, "Filter by competition enum value."),
                ("home_or_away", "string", false, "'Home' or 'Away' to scope; omit for combined.")
            ),
            Invoke = (args, json) => InvokeGetTeamRecord(engine, args, json),
        });

        Register(new Tool
        {
            Name = "get_standings",
            Description = "Calculated competition standings for one season. Returns a sorted list of teams with W/D/L and points.",
            InputSchema = Schema(
                ("season", "integer", true, "Season year, e.g. 2019."),
                ("competition", "string", true, "Competition enum value.")
            ),
            Invoke = (args, json) => InvokeGetStandings(engine, args, json),
        });

        // -- Player queries -------------------------------------------------
        Register(new Tool
        {
            Name = "search_players",
            Description = "Search players by name. Returns up to 'limit' matches ordered by overall rating desc.",
            InputSchema = Schema(
                ("name", "string", true, "Full or partial player name (case-insensitive substring)."),
                ("limit", "integer", false, "Max number of players to return (default 25).")
            ),
            Invoke = (args, json) => InvokeSearchPlayers(engine, args, json),
        });

        Register(new Tool
        {
            Name = "players_by_club",
            Description = "List players at a club, ordered by overall rating desc. Substring match on club name.",
            InputSchema = Schema(
                ("club", "string", true, "Club name (substring match, e.g. 'Flamengo', 'São Paulo')."),
                ("limit", "integer", false, "Max number of players to return (default 50).")
            ),
            Invoke = (args, json) => InvokePlayersByClub(engine, args, json),
        });

        Register(new Tool
        {
            Name = "top_brazilian_players",
            Description = "Top-rated Brazilian players in the FIFA dataset.",
            InputSchema = Schema(
                ("limit", "integer", false, "Max number of players to return (default 25).")
            ),
            Invoke = (args, json) => InvokeTopBrazilianPlayers(engine, args, json),
        });

        Register(new Tool
        {
            Name = "forwards_at_club",
            Description = "Forwards (ST/CF/LF/RF/LW/RW) at a given club, ordered by overall rating desc.",
            InputSchema = Schema(
                ("club", "string", true, "Club name substring."),
                ("limit", "integer", false, "Max number of players to return (default 20).")
            ),
            Invoke = (args, json) => InvokeForwardsAtClub(engine, args, json),
        });

        // -- Statistical analysis ------------------------------------------
        Register(new Tool
        {
            Name = "average_goals_per_match",
            Description = "Goals-per-match average over the given scope.",
            InputSchema = Schema(
                ("competition", "string", false, "Optional competition filter."),
                ("season", "integer", false, "Optional season filter.")
            ),
            Invoke = (args, json) => InvokeAverageGoals(engine, args, json),
        });

        Register(new Tool
        {
            Name = "home_win_rate",
            Description = "Home win rate (0..1) over the given scope.",
            InputSchema = Schema(
                ("competition", "string", false, "Optional competition filter."),
                ("season", "integer", false, "Optional season filter.")
            ),
            Invoke = (args, json) => InvokeHomeWinRate(engine, args, json),
        });

        Register(new Tool
        {
            Name = "biggest_wins",
            Description = "Top N matches by goal difference, optionally scoped to one competition.",
            InputSchema = Schema(
                ("limit", "integer", false, "How many wins to return (default 10)."),
                ("competition", "string", false, "Optional competition filter.")
            ),
            Invoke = (args, json) => InvokeBiggestWins(engine, args, json),
        });

        Register(new Tool
        {
            Name = "best_away_records",
            Description = "Teams with the best away win rate, with a minimum games filter to avoid 1-game outliers.",
            InputSchema = Schema(
                ("min_games", "integer", false, "Minimum away games required (default 20)."),
                ("limit", "integer", false, "How many teams to return (default 10).")
            ),
            Invoke = (args, json) => InvokeBestAwayRecords(engine, args, json),
        });
    }

    private void Register(Tool t)
    {
        _tools.Add(t);
        _byName[t.Name] = t;
    }

    public IReadOnlyList<Tool> List() => _tools;

    public Tool? Get(string name) => _byName.TryGetValue(name, out var t) ? t : null;

    // ---------------------------------------------------------------------
    // JSON Schema helper
    // ---------------------------------------------------------------------

    private static object Schema(params (string Name, string Type, bool Required, string Description)[] fields)
    {
        var properties = new Dictionary<string, object>();
        var required = new List<string>();
        foreach (var (name, type, isRequired, desc) in fields)
        {
            var prop = new Dictionary<string, object> { ["type"] = type, ["description"] = desc };
            properties[name] = prop;
            if (isRequired) required.Add(name);
        }
        return new
        {
            type = "object",
            properties,
            required = required.ToArray(),
        };
    }

    // ---------------------------------------------------------------------
    // Per-tool invokers. Each one parses its own args from a JsonObject,
    // calls the engine, and formats the result as readable text for the
    // LLM. Text format > JSON so the model can quote / summarize lines
    // directly.
    // ---------------------------------------------------------------------

    private static string InvokeFindMatchesByTeam(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var team = RequiredString(args, "team");
        var season = OptionalInt(args, "season");
        var comp = OptionalEnum<Competition>(args, "competition");
        var limit = OptionalInt(args, "limit") ?? 50;
        var matches = eng.FindMatchesByTeam(team, season, comp, limit);
        return FormatMatchList(matches, $"{team} matches");
    }

    private static string InvokeHeadToHead(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var a = RequiredString(args, "team_a");
        var b = RequiredString(args, "team_b");
        var limit = OptionalInt(args, "limit") ?? 50;
        var result = eng.HeadToHead(a, b);
        var lines = result.Matches.Take(limit)
            .Select(m => $"  - {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})")
            .ToList();
        var header = $"{result.TeamA} vs {result.TeamB} (H2H): " +
                     $"{result.TeamA} {result.AWins}W, {result.TeamB} {result.BWins}W, {result.Draws}D";
        return header + (lines.Count == 0 ? "\n  (no matches found)" : "\n" + string.Join("\n", lines));
    }

    private static string InvokeLastMatchBetween(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var a = RequiredString(args, "team_a");
        var b = RequiredString(args, "team_b");
        var m = eng.LastMatchBetween(a, b);
        return m is null
            ? $"No matches found between {a} and {b}."
            : $"{m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} on {m.Date:yyyy-MM-dd} ({m.Competition})";
    }

    private static string InvokeGetTeamRecord(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var team = RequiredString(args, "team");
        var season = OptionalInt(args, "season");
        var comp = OptionalEnum<Competition>(args, "competition");
        var homeAway = OptionalString(args, "home_or_away");
        var rec = eng.GetTeamRecord(team, season, comp, homeAway);
        if (rec is null) return $"Unknown team: {team}";
        var scope = (rec.Season.HasValue ? $" season {rec.Season}" : "") +
                    (rec.Competition is not null ? $" {rec.Competition}" : "") +
                    (rec.HomeOrAway is not null ? $" ({rec.HomeOrAway})" : "");
        return $"{rec.Team}{scope}: {rec.Played} played, " +
               $"{rec.Wins}W-{rec.Draws}D-{rec.Losses}L, " +
               $"GF {rec.GoalsFor} / GA {rec.GoalsAgainst}, " +
               $"win rate {(rec.WinRate * 100):F1}%";
    }

    private static string InvokeGetStandings(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var season = RequiredInt(args, "season");
        var comp = RequiredEnum<Competition>(args, "competition");
        var standings = eng.GetStandings(season, comp);
        if (standings.Count == 0) return $"No matches for {comp} {season}.";
        var lines = standings.Select((s, i) =>
            $"{i + 1,2}. {s.Team,-30} {s.Played,2}P {s.Wins,2}W {s.Draws,2}D {s.Losses,2}L " +
            $"(GF {s.GoalsFor,3} GA {s.GoalsAgainst,3} GD {s.GoalDifference,3}) {s.Points,3} pts");
        return $"{comp} {season} standings:\n" + string.Join("\n", lines);
    }

    private static string InvokeSearchPlayers(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var name = RequiredString(args, "name");
        var limit = OptionalInt(args, "limit") ?? 25;
        var players = eng.SearchPlayers(name, limit);
        if (players.Count == 0) return $"No players match '{name}'.";
        return string.Join("\n", players.Select((p, i) =>
            $"{i + 1,2}. {p.Name,-30} {p.Overall ?? 0,3} OVR / {p.Potential ?? 0,3} POT  " +
            $"{p.Position ?? "?",-4} {p.Club ?? "-"} ({p.Nationality ?? "-"})"));
    }

    private static string InvokePlayersByClub(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var club = RequiredString(args, "club");
        var limit = OptionalInt(args, "limit") ?? 50;
        var players = eng.PlayersByClub(club, limit);
        if (players.Count == 0) return $"No players found for club '{club}'.";
        return $"{players.Count} players at '{club}':\n" + string.Join("\n", players.Select(p =>
            $"  - {p.Name,-30} {p.Overall ?? 0,3} OVR  {p.Position ?? "?",-4} ({p.Nationality ?? "-"})"));
    }

    private static string InvokeTopBrazilianPlayers(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var limit = OptionalInt(args, "limit") ?? 25;
        var players = eng.TopBrazilianPlayers(limit);
        return string.Join("\n", players.Select((p, i) =>
            $"{i + 1,2}. {p.Name,-30} {p.Overall ?? 0,3} OVR  {p.Position ?? "?",-4} {p.Club ?? "-"}"));
    }

    private static string InvokeForwardsAtClub(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var club = RequiredString(args, "club");
        var limit = OptionalInt(args, "limit") ?? 20;
        var players = eng.ForwardsAtClub(club, limit);
        if (players.Count == 0) return $"No forwards found at '{club}'.";
        return $"Forwards at '{club}':\n" + string.Join("\n", players.Select(p =>
            $"  - {p.Name,-30} {p.Overall ?? 0,3} OVR  {p.Position ?? "?",-4}"));
    }

    private static string InvokeAverageGoals(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var comp = OptionalEnum<Competition>(args, "competition");
        var season = OptionalInt(args, "season");
        return $"Average goals per match: {eng.AverageGoalsPerMatch(comp, season):F2}";
    }

    private static string InvokeHomeWinRate(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var comp = OptionalEnum<Competition>(args, "competition");
        var season = OptionalInt(args, "season");
        return $"Home win rate: {eng.HomeWinRate(comp, season) * 100:F1}%";
    }

    private static string InvokeBiggestWins(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var limit = OptionalInt(args, "limit") ?? 10;
        var comp = OptionalEnum<Competition>(args, "competition");
        var matches = eng.BiggestWins(limit, comp);
        if (matches.Count == 0) return "No wins found.";
        return "Biggest wins:\n" + string.Join("\n", matches.Select(m =>
            $"  - {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})"));
    }

    private static string InvokeBestAwayRecords(QueryEngine eng, JsonObject args, JsonSerializerOptions json)
    {
        var minGames = OptionalInt(args, "min_games") ?? 20;
        var limit = OptionalInt(args, "limit") ?? 10;
        var records = eng.BestAwayRecords(minGames, limit);
        if (records.Count == 0) return $"No teams have played at least {minGames} away games.";
        return "Best away records:\n" + string.Join("\n", records.Select((r, i) =>
            $"{i + 1,2}. {r.Team,-30} {r.Played,3}P {r.Wins,3}W {r.Draws,2}D {r.Losses,2}L " +
            $"(win rate {r.WinRate * 100:F1}%)"));
    }

    // ---------------------------------------------------------------------
    // JSON helpers
    // ---------------------------------------------------------------------

    private static string FormatMatchList(IReadOnlyList<MatchRecord> matches, string title)
    {
        if (matches.Count == 0) return $"{title}: (no matches found)";
        var body = string.Join("\n", matches.Select(m =>
            $"  - {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})"));
        return $"{title} ({matches.Count} matches):\n{body}";
    }

    private static string RequiredString(JsonObject o, string key) =>
        o.TryGetPropertyValue(key, out var n) && n is JsonValue v && v.TryGetValue<string>(out var s) && !string.IsNullOrWhiteSpace(s)
            ? s
            : throw new InvalidOperationException($"Missing required argument: {key}");

    private static int RequiredInt(JsonObject o, string key) =>
        o.TryGetPropertyValue(key, out var n) && n is JsonValue v && v.TryGetValue<int>(out var i)
            ? i
            : throw new InvalidOperationException($"Missing required argument: {key}");

    private static string? OptionalString(JsonObject o, string key) =>
        o.TryGetPropertyValue(key, out var n) && n is JsonValue v && v.TryGetValue<string>(out var s) && !string.IsNullOrWhiteSpace(s)
            ? s
            : null;

    private static int? OptionalInt(JsonObject o, string key) =>
        o.TryGetPropertyValue(key, out var n) && n is JsonValue v && v.TryGetValue<int>(out var i) ? i : null;

    private static Competition? OptionalEnum<TEnum>(JsonObject o, string key) where TEnum : struct, Enum
    {
        var s = OptionalString(o, key);
        if (s is null) return null;
        return Enum.TryParse<Competition>(s, ignoreCase: true, out var v)
            ? v
            : throw new InvalidOperationException($"Invalid {typeof(Competition).Name} value: {s}");
    }

    private static Competition RequiredEnum<TEnum>(JsonObject o, string key) where TEnum : struct, Enum
    {
        var s = RequiredString(o, key);
        return Enum.TryParse<Competition>(s, ignoreCase: true, out var v)
            ? v
            : throw new InvalidOperationException($"Invalid {typeof(Competition).Name} value: {s}");
    }
}
