// BrazilianSoccerMcp.Server / Mcp / McpToolRegistry.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Bridges the MCP tool surface to the
// BrazilianSoccerMcp.Core query services. Each MCP tool:
//   1. Has a JSON Schema declaring its arguments (so an LLM host knows how to call).
//   2. Dispatches to the relevant Core query + ResultFormatter, returning the
//      TASK.md answer format as MCP text content.
// All tool handlers are synchronous and bound to a single SoccerDataService so
// the heavy CSV load happens once at startup and every tool call is a fast
// in-memory query (TASK.md "Query Performance").
// Error policy: argument errors return isError=true with a clear message rather
// than throwing, so the host gets a graceful MCP error instead of a crash.
// -----------------------------------------------------------------------------

using System.Text.Json;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Queries;

namespace BrazilianSoccerMcp.Server.Mcp;

internal sealed class McpToolRegistry
{
    private readonly SoccerDataService _data;
    private readonly MatchQueries _match;
    private readonly TeamQueries _team;
    private readonly PlayerQueries _player;
    private readonly CompetitionQueries _competition;
    private readonly StatisticsQueries _stats;

    public McpToolRegistry(SoccerDataService data)
    {
        _data = data;
        _match = new MatchQueries(data);
        _team = new TeamQueries(data);
        _player = new PlayerQueries(data);
        _competition = new CompetitionQueries(data);
        _stats = new StatisticsQueries(data);
    }

    // ----- catalog -----------------------------------------------------------

    public IReadOnlyList<McpToolDescriptor> ListTools()
    {
        return new[]
        {
            Tool("search_matches_for_team",
                "Find all matches a team played (home + away), optionally filtered by competition, season, or date range. Team names accept raw forms like 'Palmeiras-SP' or 'Palmeiras'.",
                Schema(new[]
                {
                    Arg("team", "string", required: true),
                    Arg("competition", "string", @enum: new[]{"brasileirao","copa_do_brasil","libertadores","historico_brasileirao","extended"}),
                    Arg("season", "integer"),
                    Arg("from", "string", description:"ISO date yyyy-MM-dd"),
                    Arg("until", "string", description:"ISO date yyyy-MM-dd"),
                })),
            Tool("matches_between_teams",
                "Find every match between two specific teams (e.g. the Fla-Flu derby), with a head-to-head summary.",
                Schema(new[]
                {
                    Arg("teamA", "string", required: true),
                    Arg("teamB", "string", required: true),
                    Arg("competition", "string"),
                    Arg("season", "integer"),
                })),
            Tool("matches_by_competition",
                "List matches in a competition, optionally restricted to a season.",
                Schema(new[]
                {
                    Arg("competition", "string", required: true, @enum: new[]{"brasileirao","copa_do_brasil","libertadores","historico_brasileirao","extended"}),
                    Arg("season", "integer"),
                    Arg("limit", "integer"),
                })),
            Tool("team_record",
                "Win/draw/loss record and goals for/against a team, optionally scoped by competition, season, and venue (home/away/both).",
                Schema(new[]
                {
                    Arg("team", "string", required: true),
                    Arg("competition", "string"),
                    Arg("season", "integer"),
                    Arg("venue", "string", @enum: new[]{"both","home","away"}),
                })),
            Tool("compare_teams",
                "Side-by-side comparison of two teams (records + head-to-head).",
                Schema(new[]
                {
                    Arg("teamA", "string", required: true),
                    Arg("teamB", "string", required: true),
                    Arg("competition", "string"),
                    Arg("season", "integer"),
                })),
            Tool("top_scorers_in_competition",
                "Teams ranked by total goals scored in a competition+season.",
                Schema(new[]
                {
                    Arg("competition", "string", required: true),
                    Arg("season", "integer", required: true),
                    Arg("limit", "integer"),
                })),
            Tool("search_players",
                "Search FIFA players by name (accent- and case-insensitive substring).",
                Schema(new[]
                {
                    Arg("name", "string", required: true),
                    Arg("limit", "integer"),
                })),
            Tool("players_by_nationality",
                "Players of a given nationality (use 'Brazil'). Sorted by overall rating.",
                Schema(new[]
                {
                    Arg("nationality", "string", required: true),
                    Arg("limit", "integer"),
                })),
            Tool("players_at_club",
                "Players at a club (accepts 'Flamengo', 'Flamengo-RJ', etc.).",
                Schema(new[]
                {
                    Arg("club", "string", required: true),
                    Arg("limit", "integer"),
                })),
            Tool("top_rated_players",
                "Top-rated FIFA players with optional nationality/club/position filters.",
                Schema(new[]
                {
                    Arg("limit", "integer"),
                    Arg("nationality", "string"),
                    Arg("club", "string"),
                    Arg("position", "string"),
                })),
            Tool("brazilian_players_at_brazilian_clubs",
                "Cross-file: Brazilian-nationality players playing at Brazilian clubs (club matched against the match datasets).",
                Schema(Array.Empty<ArgDef>())),
            Tool("standings",
                "Full standings table for a competition+season, calculated from match results. Champion is position 1.",
                Schema(new[]
                {
                    Arg("competition", "string", required: true),
                    Arg("season", "integer", required: true),
                })),
            Tool("champion",
                "The champion of a competition+season.",
                Schema(new[]
                {
                    Arg("competition", "string", required: true),
                    Arg("season", "integer", required: true),
                })),
            Tool("relegated_teams",
                "Bottom N teams (relegation zone) of a competition+season. Defaults to 4.",
                Schema(new[]
                {
                    Arg("competition", "string", required: true),
                    Arg("season", "integer", required: true),
                    Arg("count", "integer"),
                })),
            Tool("average_goals",
                "Average goals per match + home/away/draw win rates, optionally scoped.",
                Schema(new[]
                {
                    Arg("competition", "string"),
                    Arg("season", "integer"),
                })),
            Tool("biggest_wins",
                "Biggest victories in the dataset, ranked by goal difference.",
                Schema(new[]
                {
                    Arg("competition", "string"),
                    Arg("season", "integer"),
                    Arg("limit", "integer"),
                })),
            Tool("performance_trend",
                "Per-season record trend for a team in a competition.",
                Schema(new[]
                {
                    Arg("team", "string", required: true),
                    Arg("competition", "string"),
                })),
            Tool("best_home_record",
                "Team with the best home record in a scope (min 5 home matches).",
                Schema(new[]
                {
                    Arg("competition", "string"),
                    Arg("season", "integer"),
                })),
            Tool("data_summary",
                "Report data coverage: number of matches and players loaded from each source CSV.",
                Schema(Array.Empty<ArgDef>())),
        };
    }

    // ----- dispatch ----------------------------------------------------------

    public (string text, bool isError) Invoke(string toolName, JsonElement? arguments)
    {
        var args = arguments ?? default;
        try
        {
            return toolName switch
            {
                "search_matches_for_team" => Text(FormatMatchesForTeam(args)),
                "matches_between_teams" => Text(FormatMatchesBetween(args)),
                "matches_by_competition" => Text(FormatMatchesByCompetition(args)),
                "team_record" => Text(FormatTeamRecord(args)),
                "compare_teams" => Text(FormatCompare(args)),
                "top_scorers_in_competition" => Text(FormatTopScorers(args)),
                "search_players" => Text(FormatSearchPlayers(args)),
                "players_by_nationality" => Text(FormatPlayersByNationality(args)),
                "players_at_club" => Text(FormatPlayersAtClub(args)),
                "top_rated_players" => Text(FormatTopRated(args)),
                "brazilian_players_at_brazilian_clubs" => Text(FormatBrazilianAtBrazilian()),
                "standings" => Text(FormatStandings(args)),
                "champion" => Text(FormatChampion(args)),
                "relegated_teams" => Text(FormatRelegated(args)),
                "average_goals" => Text(FormatAverageGoals(args)),
                "biggest_wins" => Text(FormatBiggestWins(args)),
                "performance_trend" => Text(FormatPerformanceTrend(args)),
                "best_home_record" => Text(FormatBestHomeRecord(args)),
                "data_summary" => Text(FormatDataSummary()),
                _ => Error($"Unknown tool '{toolName}'."),
            };
        }
        catch (Exception ex)
        {
            return Error($"Tool '{toolName}' failed: {ex.Message}");
        }
    }

    // ----- handlers -----------------------------------------------------------

    private string FormatMatchesForTeam(JsonElement args)
    {
        var team = args.GetString("team") ?? throw new ArgumentException("team is required");
        var filter = BuildFilter(args);
        var matches = _match.MatchesForTeam(team, filter);
        var lines = matches.Take(GetLimit(args, 50)).Select(ResultFormatter.FormatMatchLine);
        return $"{team}: {matches.Count} match(es) in dataset\n" + string.Join("\n", lines) +
               (matches.Count > 50 ? $"\n... ({matches.Count - 50} more)" : "");
    }

    private string FormatMatchesBetween(JsonElement args)
    {
        var a = args.GetString("teamA") ?? throw new ArgumentException("teamA is required");
        var b = args.GetString("teamB") ?? throw new ArgumentException("teamB is required");
        var filter = BuildFilter(args);
        var matches = _match.MatchesBetween(a, b, filter);
        var h2h = _match.HeadToHead(a, b, filter);
        return ResultFormatter.FormatMatchesBetween(a, b, matches, h2h);
    }

    private string FormatMatchesByCompetition(JsonElement args)
    {
        var comp = ParseCompetition(args.GetString("competition"));
        var season = args.GetInt("season");
        var limit = GetLimit(args, 50);
        var matches = _match.MatchesByCompetition(comp, season);
        var lines = matches.Take(limit).Select(ResultFormatter.FormatMatchLine);
        return $"{comp} ({season}) {matches.Count} match(es):\n" + string.Join("\n", lines) +
               (matches.Count > limit ? $"\n... ({matches.Count - limit} more)" : "");
    }

    private string FormatTeamRecord(JsonElement args)
    {
        var team = args.GetString("team") ?? throw new ArgumentException("team is required");
        var comp = args.GetString("competition") is { } c ? ParseCompetition(c) : (CompetitionKind?)null;
        var season = args.GetInt("season");
        var venue = args.GetString("venue") switch { "home" => Venue.Home, "away" => Venue.Away, _ => Venue.Both };
        var record = _team.TeamRecord(team, comp, season, venue);
        var scope = BuildScopeLabel(comp, season, venue);
        return ResultFormatter.FormatTeamRecord(team, record, scope);
    }

    private string FormatCompare(JsonElement args)
    {
        var a = args.GetString("teamA") ?? throw new ArgumentException("teamA is required");
        var b = args.GetString("teamB") ?? throw new ArgumentException("teamB is required");
        var comp = args.GetString("competition") is { } c ? ParseCompetition(c) : (CompetitionKind?)null;
        var season = args.GetInt("season");
        var (ra, rb, h2h) = _team.Compare(a, b, comp, season);
        var scope = BuildScopeLabel(comp, season, Venue.Both);
        return $"{ResultFormatter.FormatTeamRecord(a, ra, scope)}\n\n" +
               $"{ResultFormatter.FormatTeamRecord(b, rb, scope)}\n\n" +
               $"Head-to-head: {h2h.TeamA} {h2h.TeamAWins} - {h2h.Draws} - {h2h.TeamB} {h2h.TeamBWins} " +
               $"({h2h.TotalMatches} scored matches)";
    }

    private string FormatTopScorers(JsonElement args)
    {
        var comp = ParseCompetition(args.GetString("competition") ?? throw new ArgumentException("competition is required"));
        var season = args.GetInt("season") ?? throw new ArgumentException("season is required");
        var limit = GetLimit(args, 10);
        var rows = _team.TopScoringTeams(comp, season, limit);
        var lines = rows.Select((x, i) => $"{i + 1}. {x.Team} - {x.GoalsFor} goals");
        return $"Top scorers in {comp} {season}:\n" + string.Join("\n", lines);
    }

    private string FormatSearchPlayers(JsonElement args)
    {
        var name = args.GetString("name") ?? throw new ArgumentException("name is required");
        var limit = GetLimit(args, 10);
        var players = _player.SearchByName(name).Take(limit).ToList();
        return ResultFormatter.FormatTopPlayers(players, $"Players matching '{name}'");
    }

    private string FormatPlayersByNationality(JsonElement args)
    {
        var nat = args.GetString("nationality") ?? throw new ArgumentException("nationality is required");
        var limit = GetLimit(args, 10);
        var players = _player.ByNationality(nat).Take(limit).ToList();
        return ResultFormatter.FormatTopPlayers(players, $"Top-rated {nat} players in dataset");
    }

    private string FormatPlayersAtClub(JsonElement args)
    {
        var club = args.GetString("club") ?? throw new ArgumentException("club is required");
        var limit = GetLimit(args, 10);
        var players = _player.ByClub(club).Take(limit).ToList();
        return ResultFormatter.FormatTopPlayers(players, $"Players at {club}");
    }

    private string FormatTopRated(JsonElement args)
    {
        var limit = GetLimit(args, 10);
        var nationality = args.GetString("nationality");
        var club = args.GetString("club");
        var position = args.GetString("position");
        var players = _player.TopRated(limit, nationality, club, position);
        var scope = new List<string>();
        if (nationality is not null) scope.Add(nationality);
        if (club is not null) scope.Add(club);
        if (position is not null) scope.Add(position);
        var title = scope.Count == 0 ? "Top-rated players in dataset" : $"Top-rated {string.Join(' ', scope)} players";
        return ResultFormatter.FormatTopPlayers(players, title);
    }

    private string FormatBrazilianAtBrazilian()
    {
        var buckets = _player.BrazilianPlayersAtBrazilianClubs();
        return ResultFormatter.FormatBuckets(buckets, "Brazilian players at Brazilian clubs");
    }

    private string FormatStandings(JsonElement args)
    {
        var comp = ParseCompetition(args.GetString("competition") ?? throw new ArgumentException("competition is required"));
        var season = args.GetInt("season") ?? throw new ArgumentException("season is required");
        var table = _competition.Standings(comp, season);
        return ResultFormatter.FormatStandings(table, $"{season} {comp}");
    }

    private string FormatChampion(JsonElement args)
    {
        var comp = ParseCompetition(args.GetString("competition") ?? throw new ArgumentException("competition is required"));
        var season = args.GetInt("season") ?? throw new ArgumentException("season is required");
        var champ = _competition.Champion(comp, season);
        if (champ is null) return $"No champion data for {comp} {season}.";
        return $"{season} {comp} champion: {champ.Team} " +
               $"({champ.Record.Points} pts, {champ.Record.Wins}W {champ.Record.Draws}D {champ.Record.Losses}L)";
    }

    private string FormatRelegated(JsonElement args)
    {
        var comp = ParseCompetition(args.GetString("competition") ?? throw new ArgumentException("competition is required"));
        var season = args.GetInt("season") ?? throw new ArgumentException("season is required");
        var count = args.GetInt("count") ?? 4;
        var rows = _competition.Relegated(comp, season, count);
        var lines = rows.Select(r => $"{r.Position}. {r.Team} - {r.Record.Points} pts ({r.Record.Wins}W {r.Record.Draws}D {r.Record.Losses}L)");
        return $"{season} {comp} relegation zone:\n" + string.Join("\n", lines);
    }

    private string FormatAverageGoals(JsonElement args)
    {
        var comp = args.GetString("competition") is { } c ? ParseCompetition(c) : (CompetitionKind?)null;
        var season = args.GetInt("season");
        var (avg, count, home, away, draw) = _stats.GoalStats(comp, season);
        var label = BuildScopeLabel(comp, season, Venue.Both);
        return $"Goals summary ({label}):\n" +
               $"- Average goals per match: {avg:F2}\n" +
               $"- Scored matches: {count}\n" +
               $"- Home win rate: {home * 100:F1}%\n" +
               $"- Away win rate: {away * 100:F1}%\n" +
               $"- Draw rate: {draw * 100:F1}%";
    }

    private string FormatBiggestWins(JsonElement args)
    {
        var comp = args.GetString("competition") is { } c ? ParseCompetition(c) : (CompetitionKind?)null;
        var season = args.GetInt("season");
        var limit = GetLimit(args, 10);
        var wins = _stats.BiggestWins(limit, comp, season);
        return ResultFormatter.FormatBiggestWins(wins, $"Biggest victories ({BuildScopeLabel(comp, season, Venue.Both)})");
    }

    private string FormatPerformanceTrend(JsonElement args)
    {
        var team = args.GetString("team") ?? throw new ArgumentException("team is required");
        var comp = args.GetString("competition") is { } c ? ParseCompetition(c) : (CompetitionKind?)null;
        var trend = _stats.PerformanceTrend(team, comp);
        var lines = trend.Select(t => $"{t.Season}: {t.Record.Describe()}");
        return $"{team} per-season trend ({(comp?.ToString() ?? "all competitions")}):\n" + string.Join("\n", lines);
    }

    private string FormatBestHomeRecord(JsonElement args)
    {
        var comp = args.GetString("competition") is { } c ? ParseCompetition(c) : (CompetitionKind?)null;
        var season = args.GetInt("season");
        var best = _stats.BestHomeRecord(comp, season);
        if (best is null) return "No team met the minimum home-match threshold.";
        var (team, rate, matches) = best.Value;
        return $"Best home record ({BuildScopeLabel(comp, season, Venue.Both)}): {team} " +
               $"- {rate * 100:F1}% home win rate over {matches} home matches";
    }

    private string FormatDataSummary()
    {
        var lines = _data.LoadCounts.Select(kv => $"- {kv.Key}: {kv.Value:N0} rows");
        var totalMatches = _data.Matches.Count;
        var totalPlayers = _data.Players.Count;
        return "Brazilian Soccer MCP data summary:\n" + string.Join("\n", lines) +
               $"\n- Total matches loaded: {totalMatches:N0}" +
               $"\n- Total players loaded: {totalPlayers:N0}";
    }

    // ----- helpers -----------------------------------------------------------

    private static MatchFilter BuildFilter(JsonElement args)
    {
        var filter = new MatchFilter();
        if (args.ValueKind == JsonValueKind.Undefined || args.ValueKind != JsonValueKind.Object)
            return filter;
        if (args.GetString("competition") is { } c)
            filter = filter with { Competition = ParseCompetition(c) };
        if (args.GetInt("season") is { } season)
            filter = filter with { Season = season };
        if (args.GetString("from") is { } fromStr && DateTime.TryParse(fromStr, out var from))
            filter = filter with { From = from };
        if (args.GetString("until") is { } untilStr && DateTime.TryParse(untilStr, out var until))
            filter = filter with { Until = until };
        return filter;
    }

    private static string BuildScopeLabel(CompetitionKind? comp, int? season, Venue venue)
    {
        var parts = new List<string>();
        if (season.HasValue) parts.Add(season.Value.ToString());
        if (comp.HasValue) parts.Add(comp.Value.ToString());
        if (venue != Venue.Both) parts.Add(venue.ToString().ToLowerInvariant());
        return parts.Count == 0 ? "all matches" : string.Join(' ', parts);
    }

    private static int GetLimit(JsonElement args, int @default)
    {
        var v = args.GetInt("limit");
        if (!v.HasValue || v.Value <= 0) return @default;
        return Math.Min(v.Value, 100);
    }

    private static CompetitionKind ParseCompetition(string? raw) => raw?.Trim().ToLowerInvariant() switch
    {
        "brasileirao" or "brasileirão" or "serie_a" or "série_a" or "serie a" => CompetitionKind.BrasileiraoSerieA,
        "copa_do_brasil" or "copa do brasil" or "copadobrasil" => CompetitionKind.CopaDoBrasil,
        "libertadores" or "copa_libertadores" => CompetitionKind.CopaLibertadores,
        "historico_brasileirao" or "historico" or "historical" => CompetitionKind.HistoricoBrasileirao,
        "extended" or "br_football" => CompetitionKind.Extended,
        "" or null => CompetitionKind.Other,
        _ => Enum.TryParse<CompetitionKind>(raw, ignoreCase: true, out var e) ? e : CompetitionKind.Other
    };

    private static (string text, bool isError) Text(string s) => (s, false);
    private static (string text, bool isError) Error(string s) => (s, true);

    // ----- schema DSL --------------------------------------------------------

    private sealed record ArgDef(string Name, string Type, bool Required, string[]? Enum, string Description);

    private static ArgDef Arg(string name, string type, bool required = false, string[]? @enum = null, string? description = null)
        => new(name, type, required, @enum, description ?? "");

    private static McpToolDescriptor Tool(string name, string description, JsonElement inputSchema)
        => new() { Name = name, Description = description, InputSchema = inputSchema };

    /// <summary>Builds a JSON Schema object describing a tool's arguments.</summary>
    private static JsonElement Schema(ArgDef[] args)
    {
        var obj = new JsonObject
        {
            ["type"] = "object",
            ["properties"] = new JsonObject(),
            ["required"] = new JsonArray(),
            ["additionalProperties"] = false,
        };
        var props = (JsonObject)obj["properties"]!;
        var required = (JsonArray)obj["required"]!;
        foreach (var a in args)
        {
            var prop = new JsonObject { ["type"] = a.Type, ["description"] = a.Description };
            if (a.Enum is not null)
            {
                var arr = new JsonArray();
                foreach (var e in a.Enum) arr.Add(JsonValue.Create(e));
                prop["enum"] = arr;
            }
            props[a.Name] = prop;
            if (a.Required) required.Add(JsonValue.Create(a.Name));
        }
        return JsonSerializer.SerializeToElement(obj);
    }
}

internal static class JsonElementExtensions
{
    public static string? GetString(this JsonElement el, string name) =>
        el.ValueKind == JsonValueKind.Object && el.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String
            ? p.GetString()
            : null;

    public static int? GetInt(this JsonElement el, string name)
    {
        if (el.ValueKind != JsonValueKind.Object || !el.TryGetProperty(name, out var p))
            return null;
        return p.ValueKind == JsonValueKind.Number && p.TryGetInt32(out var i) ? i : null;
    }
}
