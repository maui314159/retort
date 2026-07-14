using BrazilianSoccerMcp.Data;
// Brazilian Soccer MCP Server - MCP tool surface
// Context: This is the LLM-facing layer. Each method is one MCP tool, annotated
// with [McpServerTool] and parameter [Description]s so the MCP SDK can publish
// a JSON Schema for the LLM. Tools delegate to the SoccerQueryService for all
// logic and render the structured results into the formatted text blocks the
// spec specifies (match lists, head-to-head summaries, standings tables, etc.).
//
// The service is held as a lazily-initialised static singleton so the dataset is
// parsed exactly once per server process regardless of how many tool calls
// arrive. Logging goes to stderr (the server's stdout is reserved for the MCP
// protocol framing).

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public static class SoccerTools
{
    private static readonly Lazy<SoccerQueryService> Service = new(() => new SoccerQueryService());

    private static SoccerQueryService Svc => Service.Value;

    // ---------------------------------------------------------------------
    // Match queries
    // ---------------------------------------------------------------------

    [McpServerTool, Description("Search matches by team, opponent, competition, season and/or date range. Returns a formatted list newest-first.")]
    public static string SearchMatches(
        [Description("Team name (any variant, e.g. 'Flamengo', 'Palmeiras-SP'). Optional.")] string? team = null,
        [Description("Opponent team name to narrow to head-to-head fixtures. Optional.")] string? opponent = null,
        [Description("Competition: 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Brasileirão (2003-2019)', or 'all'. Optional.")] string? competition = null,
        [Description("Season year, e.g. 2023. Optional.")] int? season = null,
        [Description("Start date (YYYY-MM-DD). Optional.")] string? fromDate = null,
        [Description("End date (YYYY-MM-DD). Optional.")] string? toDate = null,
        [Description("Maximum number of matches to return (default 25).")] int limit = 25)
    {
        var filter = new MatchFilter
        {
            Team = team, Opponent = opponent,
            Competition = SoccerQueryService.ParseCompetition(competition),
            Season = season,
            From = ParseDate(fromDate), To = ParseDate(toDate),
            Limit = Math.Clamp(limit, 1, 500),
        };
        var matches = Svc.FindMatches(filter);
        if (matches.Count == 0)
            return NoMatchesMessage(team, opponent, competition, season);

        var sb = new StringBuilder();
        sb.AppendLine(DescribeFilter(team, opponent, competition, season, matches.Count));
        foreach (var m in matches)
            sb.AppendLine(FormatMatch(m));
        sb.AppendLine();
        sb.Append($"Total: {matches.Count} match(es).");
        return sb.ToString();
    }

    [McpServerTool, Description("Return the most recent match for a team (optionally vs a specific opponent) with date and score.")]
    public static string LastMatch(
        [Description("Team name.")] string team,
        [Description("Opponent team name. Optional.")] string? opponent = null)
    {
        var m = Svc.LastMatch(team, opponent);
        if (m is null)
            return opponent is null
                ? $"No matches found for '{team}' in the dataset."
                : $"No matches found between '{team}' and '{opponent}' in the dataset.";
        var sb = new StringBuilder();
        sb.AppendLine($"Last match for {Svc.TeamDisplayName(team)}" +
            (opponent is null ? "" : $" vs {Svc.TeamDisplayName(opponent)}") + ":");
        sb.AppendLine(FormatMatch(m));
        return sb.ToString();
    }

    [McpServerTool, Description("Head-to-head record between two teams with per-team wins, draws and the fixture list.")]
    public static string HeadToHead(
        [Description("First team name.")] string team1,
        [Description("Second team name.")] string team2,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season filter. Optional.")] int? season = null,
        [Description("Maximum fixtures to list (default 25).")] int limit = 25)
    {
        var hh = Svc.ComputeHeadToHead(team1, team2, SoccerQueryService.ParseCompetition(competition), season);
        var sb = new StringBuilder();
        sb.AppendLine($"{hh.Team1} vs {hh.Team2} head-to-head:");
        sb.AppendLine($"- {hh.Team1} wins: {hh.Team1Wins}");
        sb.AppendLine($"- {hh.Team2} wins: {hh.Team2Wins}");
        sb.AppendLine($"- Draws: {hh.Draws}");
        sb.AppendLine($"- Total matches: {hh.Matches.Count}");
        if (hh.Matches.Count > 0)
        {
            sb.AppendLine();
            sb.AppendLine("Fixtures (newest first):");
            foreach (var m in hh.Matches.Take(Math.Clamp(limit, 1, 500)))
                sb.AppendLine(FormatMatch(m));
        }
        return sb.ToString();
    }

    // ---------------------------------------------------------------------
    // Team queries
    // ---------------------------------------------------------------------

    [McpServerTool, Description("Compute win/draw/loss and goals tally for a team, optionally by competition, season and venue (home/away/all).")]
    public static string TeamStatistics(
        [Description("Team name.")] string team,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year. Optional.")] int? season = null,
        [Description("Venue: 'home', 'away' or 'all' (default).")] string? venue = "all")
    {
        var v = ParseVenue(venue);
        var stats = Svc.ComputeTeamStats(team, SoccerQueryService.ParseCompetition(competition), season, v);
        var sb = new StringBuilder();
        sb.AppendLine($"{stats.TeamName} record" +
            (season.HasValue ? $" ({season.Value})" : "") +
            (string.IsNullOrWhiteSpace(competition) ? "" : $" - {competition}") +
            (v == Venue.All ? "" : v == Venue.Home ? " [home]" : " [away]") + ":");
        sb.AppendLine($"- Matches: {stats.Matches}");
        sb.AppendLine($"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}");
        sb.AppendLine($"- Points: {stats.Points}");
        sb.Append($"- Win rate: {stats.WinRate:P1}");
        return sb.ToString();
    }

    [McpServerTool, Description("List the competitions a team has appeared in with match counts.")]
    public static string TeamCompetitions([Description("Team name.")] string team)
    {
        var comps = Svc.TeamCompetitions(team);
        if (comps.Count == 0)
            return $"No matches found for '{team}' in the dataset.";
        var name = Svc.TeamDisplayName(team);
        var sb = new StringBuilder();
        sb.AppendLine($"Competitions featuring {name}:");
        foreach (var (comp, (label, count)) in comps)
            sb.AppendLine($"- {label}: {count} match(es)");
        return sb.ToString();
    }

    // ---------------------------------------------------------------------
    // Competition queries
    // ---------------------------------------------------------------------

    [McpServerTool, Description("Compute league standings (by points) for a competition and season from match results. 'Brasileirão' covers 2003-2022.")]
    public static string CompetitionStandings(
        [Description("Competition: 'Brasileirão', 'Copa do Brasil', 'Libertadores', or 'Brasileirão (2003-2019)'.")] string competition,
        [Description("Season year, e.g. 2019.")] int season,
        [Description("Number of table positions to return (default 20).")] int limit = 20)
    {
        var standings = Svc.ComputeStandings(competition, season);
        if (standings.Count == 0)
            return $"No standings data for {competition} {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{standings.Count} teams in {competition} {season} standings:");
        sb.AppendLine();
        var rows = standings.Take(Math.Clamp(limit, 1, 100)).ToList();
        for (int i = 0; i < rows.Count; i++)
        {
            var t = rows[i];
            var champion = i == 0 ? " - Champion" : "";
            sb.AppendLine($"{i + 1,2}. {t.TeamName} - {t.Points} pts " +
                $"({t.Wins}W, {t.Draws}D, {t.Losses}L, GF {t.GoalsFor}, GA {t.GoalsAgainst}){champion}");
        }
        return sb.ToString();
    }

    // ---------------------------------------------------------------------
    // Statistical analysis
    // ---------------------------------------------------------------------

    [McpServerTool, Description("Biggest winning margins (by goal difference) in the dataset, optionally filtered.")]
    public static string BiggestWins(
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year. Optional.")] int? season = null,
        [Description("Number of results (default 10).")] int limit = 10)
    {
        var wins = Svc.BiggestWins(SoccerQueryService.ParseCompetition(competition), season, Math.Clamp(limit, 1, 100));
        if (wins.Count == 0)
            return "No winning matches found for the given filter.";

        var sb = new StringBuilder();
        sb.AppendLine("Biggest victories" +
            (string.IsNullOrWhiteSpace(competition) ? "" : $" - {competition}") +
            (season.HasValue ? $" ({season.Value})" : "") + ":");
        for (int i = 0; i < wins.Count; i++)
        {
            var m = wins[i];
            sb.AppendLine($"{i + 1}. {FormatMatch(m)}");
        }
        return sb.ToString();
    }

    [McpServerTool, Description("Goal-distribution analysis: average goals, home/away win and draw rates, optionally filtered.")]
    public static string GoalsAnalysis(
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year. Optional.")] int? season = null)
    {
        var g = Svc.ComputeGoalsAnalysis(SoccerQueryService.ParseCompetition(competition), season);
        if (g.Matches == 0)
            return "No scored matches found for the given filter.";

        var sb = new StringBuilder();
        var label = string.IsNullOrWhiteSpace(competition) ? "all competitions" : competition;
        sb.AppendLine($"Goal analysis ({label}{(season.HasValue ? $" {season.Value}" : "")}, {g.Matches} matches):");
        sb.AppendLine($"- Average goals per match: {g.AvgGoals:F2}");
        sb.AppendLine($"- Average home goals: {g.AvgHomeGoals:F2}, average away goals: {g.AvgAwayGoals:F2}");
        sb.AppendLine($"- Home win rate: {g.HomeWinRate:P1}, away win rate: {g.AwayWinRate:P1}, draw rate: {g.DrawRate:P1}");
        return sb.ToString();
    }

    // ---------------------------------------------------------------------
    // Player queries
    // ---------------------------------------------------------------------

    [McpServerTool, Description("Search FIFA player database by name, nationality, club, position and/or minimum overall rating.")]
    public static string SearchPlayers(
        [Description("Player name fragment. Optional.")] string? name = null,
        [Description("Nationality fragment, e.g. 'Brazil'. Optional.")] string? nationality = null,
        [Description("Club name. Optional.")] string? club = null,
        [Description("Position code or fragment, e.g. 'ST', 'GK', 'LW'. Optional.")] string? position = null,
        [Description("Minimum overall rating. Optional.")] int? minOverall = null,
        [Description("Maximum players to return (default 25).")] int limit = 25,
        [Description("Sort: 'overall' (default), 'potential', 'age', 'name'.")] string? sortBy = "overall")
    {
        var players = Svc.FindPlayers(new PlayerFilter
        {
            Name = name, Nationality = nationality, Club = club,
            Position = position, MinOverall = minOverall,
            Limit = Math.Clamp(limit, 1, 200), SortBy = sortBy,
        });
        if (players.Count == 0)
            return "No players matched the given filters.";

        var sb = new StringBuilder();
        sb.AppendLine($"{players.Count} player(s) found:");
        foreach (var p in players)
            sb.AppendLine(FormatPlayer(p));
        return sb.ToString();
    }

    [McpServerTool, Description("Top-rated players by overall, optionally filtered by nationality or club.")]
    public static string TopPlayers(
        [Description("Nationality fragment, e.g. 'Brazil'. Optional.")] string? nationality = null,
        [Description("Club name. Optional.")] string? club = null,
        [Description("Number of players to return (default 10).")] int limit = 10)
    {
        var players = Svc.FindPlayers(new PlayerFilter
        {
            Nationality = nationality, Club = club,
            Limit = Math.Clamp(limit, 1, 100), SortBy = "overall",
        });
        if (players.Count == 0)
            return "No players matched the given filters.";

        var scope = !string.IsNullOrWhiteSpace(nationality) ? $"{nationality} " :
                   (!string.IsNullOrWhiteSpace(club) ? $"{club} " : "");
        var sb = new StringBuilder();
        sb.AppendLine($"Top {players.Count} {scope}players by overall rating:");
        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position ?? "?"}, Club: {p.Club ?? "Free"}");
        }
        return sb.ToString();
    }

    // ---------------------------------------------------------------------
    // Formatting helpers
    // ---------------------------------------------------------------------

    internal static string FormatMatch(Match m)
    {
        var date = m.Date?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "unknown date";
        var round = string.IsNullOrWhiteSpace(m.Round) ? "" : $" Round {m.Round}";
        return $"{date}: {TeamNormalizer.DisplayName(m.HomeTeam)} {m.HomeGoal}-{m.AwayGoal} {TeamNormalizer.DisplayName(m.AwayTeam)} ({m.CompetitionLabel}{round})";
    }

    private static string FormatPlayer(Player p)
    {
        return $"- {p.Name} - Overall: {p.Overall}, Potential: {p.Potential}, " +
               $"Position: {p.Position ?? "?"}, Age: {p.Age}, Nationality: {p.Nationality}, " +
               $"Club: {p.Club ?? "Free"}";
    }

    private static string DescribeFilter(string? team, string? opponent, string? competition, int? season, int count)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(team)) parts.Add(Svc.TeamDisplayName(team));
        if (!string.IsNullOrWhiteSpace(opponent)) parts.Add("vs " + Svc.TeamDisplayName(opponent));
        if (!string.IsNullOrWhiteSpace(competition)) parts.Add(competition);
        if (season.HasValue) parts.Add(season.Value.ToString(CultureInfo.InvariantCulture));
        var subject = parts.Count == 0 ? "All matches" : string.Join(" ", parts);
        return $"{subject} ({count} match(es)):";
    }

    private static string NoMatchesMessage(string? team, string? opponent, string? competition, int? season)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(team)) parts.Add($"team='{team}'");
        if (!string.IsNullOrWhiteSpace(opponent)) parts.Add($"opponent='{opponent}'");
        if (!string.IsNullOrWhiteSpace(competition)) parts.Add($"competition='{competition}'");
        if (season.HasValue) parts.Add($"season={season}");
        var detail = parts.Count == 0 ? "" : $" for {string.Join(", ", parts)}";
        return $"No matches found{detail}. Check the team name spelling or broaden the filters.";
    }

    private static DateOnly? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateOnly.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d) ? d : null;
    }

    private static Venue ParseVenue(string? v)
    {
        if (string.IsNullOrWhiteSpace(v)) return Venue.All;
        return v.Trim().ToLowerInvariant() switch
        {
            "home" or "casa" or "mandante" => Venue.Home,
            "away" or "fora" or "visitante" => Venue.Away,
            _ => Venue.All,
        };
    }
}
