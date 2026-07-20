using System.Globalization;
using System.Text.Json;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// MCP tool surface: 13 tools covering the five required query categories
/// (matches, teams, players, competitions, statistics). Each tool returns a
/// human-readable text answer formatted after the specification's examples.
/// </summary>
public sealed class ToolRegistry
{
    public sealed record ToolDef(
        string Name,
        string Description,
        object InputSchema,
        Func<Dictionary<string, JsonElement>, string> Handler);

    private readonly List<ToolDef> _tools = new();

    public IReadOnlyList<ToolDef> Tools => _tools;

    public ToolRegistry(KnowledgeGraph graph)
    {
        var queries = new MatchQueryService(graph);
        var analytics = new TeamAnalyticsService(graph, queries);
        var players = new PlayerQueryService(graph);

        Register("find_matches",
            "Find soccer matches by team, opponent, competition, season, date range, venue or round. "
            + "Covers Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores.",
            Schema(new
            {
                team = Prop("string", "Team name, e.g. 'Flamengo', 'Palmeiras-SP', 'Grêmio'"),
                opponent = Prop("string", "Second team for matches between the two"),
                competition = Prop("string", "Competition name or alias, e.g. 'Brasileirão', 'Serie A', 'Copa do Brasil', 'Libertadores', 'Serie B'"),
                season = Prop("integer", "Season year, e.g. 2023"),
                from_date = Prop("string", "Start date (yyyy-MM-dd or dd/MM/yyyy)"),
                to_date = Prop("string", "End date (yyyy-MM-dd or dd/MM/yyyy)"),
                venue = Prop("string", "'home' or 'away' (requires team)"),
                round = Prop("string", "Round number ('22') or cup stage ('final', 'semifinals', 'group stage')"),
                limit = Prop("integer", "Max matches to return (default 10, max 50)"),
            }),
            args =>
            {
                var filter = BuildFilter(args, defaultLimit: 10, maxLimit: 50);
                var total = queries.Count(filter);
                var matches = queries.Find(filter, out var notes);
                if (matches.Count == 0)
                    return Join(notes.Append("No matches found for the given criteria."));

                var header = DescribeFilter(filter, queries);
                var lines = new List<string> { $"{header}: showing {matches.Count} of {total} match(es) in dataset" };
                lines.AddRange(notes);
                lines.AddRange(matches.Select(m => "- " + m));
                return string.Join('\n', lines);
            });

        Register("head_to_head",
            "Compare two teams head-to-head: all matches between them plus the win/draw tally.",
            Schema(new
            {
                team1 = Prop("string", "First team name"),
                team2 = Prop("string", "Second team name"),
                competition = Prop("string", "Optional competition filter"),
                limit = Prop("integer", "Max matches to list (default 15)"),
            }, "team1", "team2"),
            args =>
            {
                var limit = GetInt(args, "limit") ?? 15;
                var h2h = analytics.GetHeadToHead(Req(args, "team1"), Req(args, "team2"), GetString(args, "competition"), limit);
                if (h2h.Matches.Count == 0)
                    return $"No matches between {h2h.Team1Display} and {h2h.Team2Display} found in the dataset.";

                var lines = new List<string>
                {
                    $"{h2h.Team1Display} vs {h2h.Team2Display} ({h2h.Matches.Count} match(es) in dataset, most recent first):",
                };
                lines.AddRange(h2h.Matches.Select(m => "- " + m));
                lines.Add($"Head-to-head in dataset: {h2h.Team1Display} {h2h.Team1Wins} wins, "
                          + $"{h2h.Team2Display} {h2h.Team2Wins} wins, {h2h.Draws} draws");
                return string.Join('\n', lines);
            });

        Register("team_statistics",
            "Win/draw/loss record, goals for/against and win rate for a team, "
            + "optionally filtered by season, competition and venue (home/away).",
            Schema(new
            {
                team = Prop("string", "Team name"),
                season = Prop("integer", "Season year"),
                competition = Prop("string", "Competition name or alias"),
                venue = Prop("string", "'home' or 'away'"),
            }, "team"),
            args =>
            {
                var rec = analytics.GetTeamRecord(Req(args, "team"), GetInt(args, "season"),
                    GetString(args, "competition"), GetString(args, "venue"));
                var scope = DescribeScope(GetInt(args, "season"), GetString(args, "competition"), GetString(args, "venue"), queries);
                var lines = new List<string>
                {
                    $"{rec.TeamDisplay} record ({scope}):",
                    $"Matches: {rec.Played} | Wins: {rec.Wins}, Draws: {rec.Draws}, Losses: {rec.Losses}",
                    $"Goals For: {rec.GoalsFor}, Goals Against: {rec.GoalsAgainst} | Goal Difference: {Signed(rec.GoalDifference)}",
                    $"Win rate: {Pct(rec.WinRate)}",
                };
                if (rec.Unplayed > 0)
                    lines.Add($"({rec.Unplayed} scheduled match(es) without a recorded score are excluded.)");
                return string.Join('\n', lines);
            });

        Register("competition_standings",
            "League table for a season computed from match results (3 pts win, 1 pt draw). "
            + "Defaults to Brasileirão Série A.",
            Schema(new
            {
                season = Prop("integer", "Season year, e.g. 2019"),
                competition = Prop("string", "Competition (default: Brasileirão Série A)"),
                limit = Prop("integer", "Max rows (default 20)"),
            }, "season"),
            args =>
            {
                var season = GetInt(args, "season")
                             ?? throw new ArgumentException("Parameter 'season' is required.");
                var competition = GetString(args, "competition");
                var rows = analytics.GetStandings(season, competition);
                if (rows.Count == 0)
                    return $"No played matches found for season {season}.";
                var compName = queries.ResolveCompetition(competition) ?? DataLoader.SerieA;
                var limit = Math.Min(GetInt(args, "limit") ?? 20, 100);
                var lines = new List<string>
                {
                    $"{season} {compName} standings (computed from {rows.Sum(r => r.Played) / 2} matches):",
                };
                lines.AddRange(rows.Take(limit).Select(r =>
                    $"{r.Position,2}. {r.Team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L, "
                    + $"GF {r.GoalsFor}, GA {r.GoalsAgainst})"));
                return string.Join('\n', lines);
            });

        Register("competition_stats",
            "Aggregate statistics for a competition (or all): match counts, average goals "
            + "per match, home win / draw / away win rates.",
            Schema(new
            {
                competition = Prop("string", "Competition name or alias (omit for all competitions)"),
                season = Prop("integer", "Optional season year"),
            }),
            args =>
            {
                var stats = analytics.GetCompetitionStats(GetString(args, "competition"), GetInt(args, "season"));
                var scope = stats.Season is { } s ? $"{s}" : "all seasons in dataset";
                return string.Join('\n',
                    $"{stats.Competition} ({scope}):",
                    $"Matches: {stats.TotalMatches} ({stats.PlayedMatches} played)",
                    $"Total goals: {stats.TotalGoals} | Average goals per match: {F2(stats.AvgGoalsPerMatch)}",
                    $"Home wins: {Pct(stats.HomeWinRate)} | Draws: {Pct(stats.DrawRate)} | Away wins: {Pct(stats.AwayWinRate)}");
            });

        Register("biggest_wins",
            "Largest victory margins in the dataset, optionally filtered by competition/season.",
            Schema(new
            {
                competition = Prop("string", "Competition name or alias"),
                season = Prop("integer", "Season year"),
                limit = Prop("integer", "Max results (default 10)"),
            }),
            args =>
            {
                var wins = analytics.GetBiggestWins(GetString(args, "competition"), GetInt(args, "season"),
                    GetInt(args, "limit") ?? 10);
                if (wins.Count == 0)
                    return "No matches found for the given criteria.";
                var comp = GetString(args, "competition") is { } c
                    ? queries.ResolveCompetition(c) ?? c
                    : "all competitions";
                var lines = new List<string> { $"Biggest victories ({comp}):" };
                lines.AddRange(wins.Select((m, i) => $"{i + 1}. {m}"));
                return string.Join('\n', lines);
            });

        Register("search_players",
            "Search FIFA players by name, nationality (e.g. 'Brazil'), club, position "
            + "(e.g. 'ST', 'LW', 'GK') and minimum overall rating. Best-rated first.",
            Schema(new
            {
                name = Prop("string", "Player name (substring, accent-insensitive)"),
                nationality = Prop("string", "Nationality, e.g. 'Brazil'"),
                club = Prop("string", "Club name (substring or canonical)"),
                position = Prop("string", "Position code, e.g. 'ST', 'CDM', 'GK'"),
                min_overall = Prop("integer", "Minimum FIFA overall rating"),
                forwards_only = Prop("boolean", "Restrict to attacking positions (ST/CF/LW/RW/LF/RF)"),
                limit = Prop("integer", "Max results (default 15)"),
            }),
            args =>
            {
                var filter = new PlayerQueryService.PlayerFilter
                {
                    Name = GetString(args, "name"),
                    Nationality = GetString(args, "nationality"),
                    Club = GetString(args, "club"),
                    Position = GetString(args, "position"),
                    MinOverall = GetInt(args, "min_overall"),
                    ForwardsOnly = GetBool(args, "forwards_only") ?? false,
                    Limit = Math.Min(GetInt(args, "limit") ?? 15, 100),
                };
                var total = players.Count(filter);
                var found = players.Search(filter);
                if (found.Count == 0)
                    return "No players found for the given criteria.";
                var lines = new List<string> { $"Players matching criteria: showing {found.Count} of {total}" };
                lines.AddRange(found.Select((p, i) => $"{i + 1}. {p}"));
                return string.Join('\n', lines);
            });

        Register("club_players",
            "Top-rated FIFA players at a club, e.g. 'Grêmio', 'Santos', 'Fluminense'. "
            + "Uses the same team-name normalization as the match data.",
            Schema(new
            {
                club = Prop("string", "Club name"),
                limit = Prop("integer", "Max players (default 10)"),
            }, "club"),
            args =>
            {
                var found = players.GetClubPlayers(Req(args, "club"), GetInt(args, "limit") ?? 10, out var note);
                if (found.Count == 0)
                    return note ?? "No players found.";
                var lines = new List<string> { $"Top-rated players at {found[0].Club} (FIFA dataset):" };
                lines.AddRange(found.Select((p, i) =>
                    $"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position ?? "?"}, Age: {p.Age?.ToString() ?? "?"}"));
                return string.Join('\n', lines);
            });

        Register("top_players",
            "Highest-rated players in the FIFA dataset, optionally filtered by nationality "
            + "and/or position (e.g. top Brazilian forwards).",
            Schema(new
            {
                nationality = Prop("string", "Nationality filter, e.g. 'Brazil'"),
                position = Prop("string", "Position code filter"),
                limit = Prop("integer", "Max results (default 10)"),
            }),
            args =>
            {
                var found = players.GetTopPlayers(GetString(args, "nationality"), GetString(args, "position"),
                    Math.Min(GetInt(args, "limit") ?? 10, 100));
                if (found.Count == 0)
                    return "No players found for the given criteria.";
                var scope = GetString(args, "nationality") is { } n ? $"{n} players" : "players";
                var lines = new List<string> { $"Top-rated {scope} in dataset:" };
                lines.AddRange(found.Select((p, i) => $"{i + 1}. {p}"));
                return string.Join('\n', lines);
            });

        Register("brazilian_players_summary",
            "Summary of Brazilian players in the FIFA dataset: total count, top rated, "
            + "and per-club counts for the Brazilian clubs present in the data.",
            Schema(new
            {
                limit = Prop("integer", "Max rows per section (default 10)"),
            }),
            args =>
            {
                var limit = Math.Min(GetInt(args, "limit") ?? 10, 50);
                var total = players.Count(new PlayerQueryService.PlayerFilter { Nationality = "Brazil" });
                var top = players.GetTopPlayers("Brazil", null, limit);
                var clubs = players.GetBrazilianClubSummary(limit);

                var lines = new List<string> { $"Brazilian players in FIFA dataset: {total}", "", "Top-rated:" };
                lines.AddRange(top.Select((p, i) => $"{i + 1}. {p}"));
                lines.Add("");
                lines.Add("Brazilian players at Brazilian clubs (FIFA dataset):");
                lines.AddRange(clubs.Select(c =>
                    $"- {c.Club}: {c.Count} players (avg rating: {c.AvgOverall.ToString("0.0", CultureInfo.InvariantCulture)})"));
                return string.Join('\n', lines);
            });

        Register("list_competitions",
            "List the competitions in the dataset with season coverage and match counts.",
            Schema(new { }),
            _ =>
            {
                var lines = new List<string> { "Competitions in dataset:" };
                foreach (var comp in graph.Competitions)
                {
                    var matches = graph.MatchesByCompetition[comp];
                    var seasons = matches.Where(m => m.Season is not null).Select(m => m.Season!.Value)
                        .Distinct().Order().ToList();
                    var span = seasons.Count == 0 ? "no dated seasons"
                        : $"{seasons.First()}-{seasons.Last()} ({seasons.Count} seasons)";
                    lines.Add($"- {comp}: {matches.Count} matches, {span}");
                }
                lines.Add($"Total: {graph.Matches.Count} matches from {graph.SourceContributions.Count} files "
                          + $"({graph.TotalMatchRowsRead} raw rows before cross-source dedup).");
                return string.Join('\n', lines);
            });

        Register("list_teams",
            "List teams in the dataset, optionally filtered by competition, with match counts. "
            + "Useful for discovering exact team names before querying.",
            Schema(new
            {
                competition = Prop("string", "Competition name or alias"),
                name_contains = Prop("string", "Substring filter on team names"),
                limit = Prop("integer", "Max teams (default 50)"),
            }),
            args =>
            {
                IEnumerable<KnowledgeGraph.TeamNode> teams = graph.Teams.Values;
                if (!string.IsNullOrWhiteSpace(GetString(args, "competition")))
                {
                    var comp = queries.ResolveCompetition(GetString(args, "competition"))
                               ?? throw new KeyNotFoundException($"Competition '{GetString(args, "competition")}' not found.");
                    teams = teams.Where(t => t.Matches.Any(m => m.Competition == comp));
                }
                if (!string.IsNullOrWhiteSpace(GetString(args, "name_contains")))
                {
                    var needle = TeamNameNormalizer.Normalize(GetString(args, "name_contains"));
                    teams = teams.Where(t => t.Key.Contains(needle, StringComparison.Ordinal));
                }
                var list = teams.OrderByDescending(t => t.Matches.Count)
                    .Take(Math.Min(GetInt(args, "limit") ?? 50, 200))
                    .ToList();
                if (list.Count == 0)
                    return "No teams found for the given criteria.";
                var lines = new List<string> { $"Teams ({list.Count} shown):" };
                lines.AddRange(list.Select(t => $"- {t.DisplayName} ({t.Matches.Count} matches)"));
                return string.Join('\n', lines);
            });

        Register("graph_stats",
            "Knowledge-graph statistics: node counts by kind, edge count, and per-file "
            + "contributions to the unified dataset.",
            Schema(new { }),
            _ =>
            {
                var s = graph.Stats();
                var lines = new List<string>
                {
                    "Knowledge graph contents:",
                    $"- Team nodes: {s.TeamNodes}",
                    $"- Player nodes: {s.PlayerNodes}",
                    $"- Competition nodes: {s.CompetitionNodes}",
                    $"- Season nodes: {s.SeasonNodes}",
                    $"- Match nodes: {s.MatchNodes}",
                    $"- Edges (team-match, match-competition/season, player-club): {s.Edges}",
                    "",
                    "Source file contributions (matches kept after per-season source dedup):",
                };
                lines.AddRange(graph.SourceContributions.OrderBy(kv => kv.Key)
                    .Select(kv => $"- {kv.Key}: {kv.Value} matches"));
                return string.Join('\n', lines);
            });
    }

    // ---- filter construction ---------------------------------------------------

    private static MatchFilter BuildFilter(Dictionary<string, JsonElement> args, int defaultLimit, int maxLimit)
    {
        return new MatchFilter
        {
            Team = GetString(args, "team"),
            Opponent = GetString(args, "opponent"),
            Competition = GetString(args, "competition"),
            Season = GetInt(args, "season"),
            From = FlexibleDateParser.ParseFilter(GetString(args, "from_date")),
            To = FlexibleDateParser.ParseFilter(GetString(args, "to_date")),
            Venue = GetString(args, "venue"),
            Round = GetString(args, "round"),
            Limit = Math.Min(GetInt(args, "limit") ?? defaultLimit, maxLimit),
        };
    }

    private static string DescribeFilter(MatchFilter f, MatchQueryService queries)
    {
        var parts = new List<string>();
        if (f.Team is not null) parts.Add(f.Opponent is not null ? $"{f.Team} vs {f.Opponent}" : f.Team);
        if (f.Competition is not null) parts.Add(queries.ResolveCompetition(f.Competition) ?? f.Competition);
        if (f.Season is { } s) parts.Add(s.ToString(CultureInfo.InvariantCulture));
        if (f.Venue is not null) parts.Add(f.Venue);
        if (f.Round is not null) parts.Add($"round/stage '{f.Round}'");
        if (f.From is { } from) parts.Add($"from {from:yyyy-MM-dd}");
        if (f.To is { } to) parts.Add($"to {to:yyyy-MM-dd}");
        return parts.Count == 0 ? "All matches" : "Matches (" + string.Join(", ", parts) + ")";
    }

    private static string DescribeScope(int? season, string? competition, string? venue, MatchQueryService queries)
    {
        var parts = new List<string>();
        if (venue is not null) parts.Add(venue.Equals("home", StringComparison.OrdinalIgnoreCase) ? "home matches" : venue.Equals("away", StringComparison.OrdinalIgnoreCase) ? "away matches" : venue);
        if (season is { } s) parts.Add(s.ToString(CultureInfo.InvariantCulture));
        if (competition is not null) parts.Add(queries.ResolveCompetition(competition) ?? competition);
        return parts.Count == 0 ? "all matches in dataset" : string.Join(", ", parts);
    }

    // ---- JSON schema helpers -----------------------------------------------------

    private static object Prop(string type, string description) =>
        new Dictionary<string, object?> { ["type"] = type, ["description"] = description };

    private static object Schema(object properties, params string[] required) =>
        new Dictionary<string, object?>
        {
            ["type"] = "object",
            ["properties"] = properties,
            ["required"] = required,
            ["additionalProperties"] = false,
        };

    // ---- argument extraction -------------------------------------------------------

    private static string Req(Dictionary<string, JsonElement> args, string name) =>
        GetString(args, name) ?? throw new ArgumentException($"Parameter '{name}' is required.");

    private static string? GetString(Dictionary<string, JsonElement> args, string name)
    {
        if (!args.TryGetValue(name, out var el))
            return null;
        return el.ValueKind switch
        {
            JsonValueKind.String => string.IsNullOrWhiteSpace(el.GetString()) ? null : el.GetString(),
            JsonValueKind.Number => el.GetRawText(),
            JsonValueKind.True => "true",
            JsonValueKind.False => "false",
            _ => null,
        };
    }

    private static int? GetInt(Dictionary<string, JsonElement> args, string name)
    {
        if (!args.TryGetValue(name, out var el))
            return null;
        if (el.ValueKind == JsonValueKind.Number && el.TryGetInt32(out var i))
            return i;
        if (el.ValueKind == JsonValueKind.String
            && int.TryParse(el.GetString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var s))
            return s;
        return null;
    }

    private static bool? GetBool(Dictionary<string, JsonElement> args, string name)
    {
        if (!args.TryGetValue(name, out var el))
            return null;
        return el.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.String => bool.TryParse(el.GetString(), out var b) ? b : null,
            _ => null,
        };
    }

    // ---- formatting -------------------------------------------------------------------

    private static string Pct(double rate) =>
        (rate * 100).ToString("0.0", CultureInfo.InvariantCulture) + "%";

    private static string F2(double value) => value.ToString("0.00", CultureInfo.InvariantCulture);

    private static string Signed(int value) => value >= 0 ? "+" + value : value.ToString(CultureInfo.InvariantCulture);

    private static string Join(IEnumerable<string> lines) => string.Join('\n', lines);

    private void Register(string name, string description, object inputSchema,
        Func<Dictionary<string, JsonElement>, string> handler) =>
        _tools.Add(new ToolDef(name, description, inputSchema, handler));

    /// <summary>MCP result object for tools/list.</summary>
    public object ListToolsResult() => new
    {
        tools = _tools.Select(t => new
        {
            name = t.Name,
            description = t.Description,
            inputSchema = t.InputSchema,
        }),
    };

    /// <summary>Executes a tool call, converting domain errors into MCP isError results.</summary>
    public (string Text, bool IsError) Call(string name, Dictionary<string, JsonElement>? args)
    {
        var tool = _tools.FirstOrDefault(t => t.Name == name);
        if (tool is null)
            return ($"Unknown tool '{name}'. Available: {string.Join(", ", _tools.Select(t => t.Name))}.", true);

        try
        {
            return (tool.Handler(args ?? new Dictionary<string, JsonElement>()), false);
        }
        catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException)
        {
            return (ex.Message, true);
        }
    }
}
