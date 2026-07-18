// =============================================================================
// BrazilianSoccerMcp - MCP Tools
// -----------------------------------------------------------------------------
// Context: These are the tools the MCP server exposes to the connected LLM.
// Each tool is a thin, well-described wrapper over SoccerDataRepository that
// turns query results into human-readable text. The descriptions are written
// for an LLM to know when to call which tool and what arguments to pass.
//
// The repository is injected via DI (registered as a singleton in Program.cs);
// the MCP SDK instantiates this tool type through the container.
// =============================================================================

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class SoccerTools
{
    private readonly SoccerDataRepository _repo;
    public SoccerTools(SoccerDataRepository repo) => _repo = repo;

    // --------------------------------------------------------------- 1. matches

    [McpServerTool, Description(
        "Search Brazilian soccer matches across all loaded datasets. Combine any " +
        "filters: a team, an opponent, a competition (Brasileirão/Série A, Série B, " +
        "Série C, Copa do Brasil, Libertadores), a season year, and a date range " +
        "(ISO yyyy-MM-dd). Returns recent matches with date, score, competition and round.")]
    public string SearchMatches(
        [Description("Team name, e.g. 'Flamengo', 'Palmeiras-SP', 'São Paulo'")] string? team = null,
        [Description("Opponent team name to further restrict to head-to-head fixtures")] string? opponent = null,
        [Description("Competition: Brasileirão, Série A/B/C, Copa do Brasil, Libertadores")] string? competition = null,
        [Description("Season year, e.g. 2023")] int? season = null,
        [Description("Earliest date (ISO yyyy-MM-dd), inclusive")] string? dateFrom = null,
        [Description("Latest date (ISO yyyy-MM-dd), inclusive")] string? dateTo = null,
        [Description("Maximum number of matches to return (default 25)")] int limit = 25)
    {
        var from = ParseDate(dateFrom);
        var to = ParseDate(dateTo);
        var ms = _repo.SearchMatches(team, opponent, competition, season, from, to)
            .OrderByDescending(m => m.Date).Take(Math.Max(1, limit)).ToList();
        if (ms.Count == 0) return NoMatches(team, opponent, competition, season);

        var sb = new StringBuilder();
        var title = team is null && opponent is null ? "Matches" : $"{team ?? "any"} vs {opponent ?? "any"}";
        sb.AppendLine($"{title} — {ms.Count} match(es) found:");
        foreach (var m in ms)
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} " +
                          $"({m.Competition}" + RoundOrStage(m) + ")");
        return sb.ToString().TrimEnd();
    }

    // ----------------------------------------------------------------- 2. teams

    [McpServerTool, Description(
        "Compute head-to-head record between two teams across all datasets, listing " +
        "their fixtures and the overall win/draw/win tally.")]
    public string HeadToHead(
        [Description("First team name")] string team1,
        [Description("Second team name")] string team2,
        [Description("Optional competition filter")] string? competition = null,
        [Description("Optional season year")] int? season = null)
    {
        var h2h = _repo.GetHeadToHead(team1, team2, competition, season);
        var sb = new StringBuilder();
        sb.AppendLine($"{h2h.Team1} vs {h2h.Team2} — head-to-head ({h2h.Matches.Count} matches):");
        foreach (var m in h2h.Matches.Take(30))
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition}{RoundOrStage(m)})");
        if (h2h.Matches.Count > 30) sb.AppendLine($"- ... ({h2h.Matches.Count - 30} more)");
        sb.AppendLine($"Record: {h2h.Team1} {h2h.Team1Wins} wins, {h2h.Team2} {h2h.Team2Wins} wins, {h2h.Draws} draws");
        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description(
        "Aggregate statistics for a team: matches, wins, draws, losses, goals for/against " +
        "and win rate. Optionally filter by season, competition, and venue (home/away/any).")]
    public string TeamStatistics(
        [Description("Team name")] string team,
        [Description("Season year (optional)")] int? season = null,
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Venue: 'home', 'away' or 'any' (default any)")] string venue = "any")
    {
        var key = _repo.ResolveTeamKey(team);
        var s = _repo.GetTeamStatistics(key, season, competition, venue);
        var sb = new StringBuilder();
        var where = !string.IsNullOrEmpty(venue) && !venue.Equals("any", StringComparison.OrdinalIgnoreCase)
            ? $" ({venue})" : "";
        sb.AppendLine($"{_repo.DisplayName(key)}{where} statistics" +
                      $"{(season is null ? "" : $" {season}")}{CompLabel(competition)}:");
        sb.AppendLine($"- Matches: {s.Matches}");
        sb.AppendLine($"- Wins: {s.Wins}, Draws: {s.Draws}, Losses: {s.Losses}");
        sb.AppendLine($"- Goals For: {s.GoalsFor}, Goals Against: {s.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {s.WinRate:F1}%");
        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description(
        "List all competitions a team has appeared in across the loaded datasets.")]
    public string TeamCompetitions([Description("Team name")] string team)
    {
        var comps = _repo.TeamCompetitions(team);
        var key = _repo.ResolveTeamKey(team);
        if (comps.Count == 0) return $"No matches found for '{team}'.";
        return $"{_repo.DisplayName(key)} appeared in {comps.Count} competition(s):\n- " +
               string.Join("\n- ", comps);
    }

    // --------------------------------------------------------------- 3. players

    [McpServerTool, Description(
        "Search the FIFA player database. Filter by name, nationality, club, playing " +
        "position and minimum overall rating. Results are sorted by overall rating " +
        "(highest first). Use nationality 'Brazil' to find Brazilian players.")]
    public string SearchPlayers(
        [Description("Name fragment, e.g. 'Neymar' or 'Gabriel Barbosa'")] string? name = null,
        [Description("Nationality, e.g. 'Brazil' or 'Argentina'")] string? nationality = null,
        [Description("Club name fragment, e.g. 'Flamengo' or 'São Paulo'")] string? club = null,
        [Description("Position code, e.g. ST, LW, GK, CDM, CB")] string? position = null,
        [Description("Minimum FIFA overall rating")] int? minOverall = null,
        [Description("Maximum number of players to return (default 20)")] int limit = 20)
    {
        var ps = _repo.SearchPlayers(name, nationality, club, position, minOverall)
            .OrderByDescending(p => p.Overall).Take(Math.Max(1, limit)).ToList();
        if (ps.Count == 0) return NoPlayers(name, nationality, club, position, minOverall);

        var sb = new StringBuilder();
        sb.AppendLine($"Found {ps.Count} player(s):");
        for (int i = 0; i < ps.Count; i++)
        {
            var p = ps[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, " +
                          $"Nationality: {p.Nationality}, Club: {p.Club}" +
                          (p.Age > 0 ? $", Age: {p.Age}" : ""));
        }
        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description(
        "Summarize Brazilian players who play for Brazilian clubs in the FIFA dataset, " +
        "grouped by club with counts and average ratings.")]
    public string BrazilianPlayersAtBrazilianClubs()
    {
        var rows = _repo.BrazilianClubsSummary();
        if (rows.Count == 0) return "No Brazilian players at Brazilian clubs found.";
        var sb = new StringBuilder();
        sb.AppendLine("Brazilian players at Brazilian clubs (FIFA dataset):");
        foreach (var r in rows)
            sb.AppendLine($"- {r.Club}: {r.Count} players (avg rating: {r.AvgRating:F1})");
        return sb.ToString().TrimEnd();
    }

    // --------------------------------------------------------- 4. competitions

    [McpServerTool, Description(
        "Compute a league standings table for a round-robin competition season " +
        "(Brasileirão Série A/B/C). Standings are calculated from match results. " +
        "The champion (rank 1) and the bottom four (relegated) are flagged.")]
    public string CompetitionStandings(
        [Description("Competition, e.g. 'Brasileirão' or 'Série A'")] string competition,
        [Description("Season year, e.g. 2019")] int season)
    {
        var st = _repo.GetStandings(competition, season);
        if (st is null)
            return $"No standings available for '{competition}' in {season} " +
                   "(try Brasileirão/Série A between 2003-2023, or Série B/C 2014-2023).";

        var sb = new StringBuilder();
        sb.AppendLine($"{st.Competition} {st.Season} standings (source: {st.Source}, {st.Rows.Count} teams):");
        sb.AppendLine("Pos  Team                       P   W   D   L   GF  GA  GD  Pts");
        for (int i = 0; i < st.Rows.Count; i++)
        {
            var r = st.Rows[i];
            var tag = r.Champion ? " ★" : (r.Relegated ? " ⤓" : "");
            sb.AppendLine($"{i + 1,-4} {Pad(r.Team, 25)} {r.Played,-3} {r.Wins,-3} {r.Draws,-3} {r.Losses,-3} " +
                          $"{r.GoalsFor,-3} {r.GoalsAgainst,-3} {r.GoalDiff,+3} {r.Points,-3}{tag}");
        }
        return sb.ToString().TrimEnd();
    }

    // ----------------------------------------------------- 5. statistics

    [McpServerTool, Description(
        "List the biggest victories (largest goal margins) across the datasets, " +
        "optionally filtered by competition and/or season.")]
    public string BiggestWins(
        [Description("Optional competition filter")] string? competition = null,
        [Description("Optional season year")] int? season = null,
        [Description("Maximum number of results (default 10)")] int limit = 10)
    {
        var ms = _repo.BiggestWins(competition, season, Math.Max(1, limit)).ToList();
        if (ms.Count == 0) return NoMatches(null, null, competition, season);
        var sb = new StringBuilder();
        sb.AppendLine("Biggest victories:");
        for (int i = 0; i < ms.Count; i++)
        {
            var m = ms[i];
            sb.AppendLine($"{i + 1}. {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} " +
                          $"({m.Competition}{RoundOrStage(m)})");
        }
        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description(
        "Aggregate scoring statistics: average goals per match and home win / away win " +
        "/ draw percentages. Optionally filter by competition and/or season.")]
    public string AverageGoals(
        [Description("Optional competition filter")] string? competition = null,
        [Description("Optional season year")] int? season = null)
    {
        var g = _repo.AverageGoals(competition, season);
        if (g.Matches == 0) return NoMatches(null, null, competition, season);
        return $"Goals statistics{CompLabel(competition)}{(season is null ? "" : $" {season}")} " +
               $"({g.Matches} matches):\n" +
               $"- Average goals per match: {g.AvgGoals:F2}\n" +
               $"- Home win rate: {g.HomeWinPct:F1}%\n" +
               $"- Away win rate: {g.AwayWinPct:F1}%\n" +
               $"- Draw rate: {g.DrawPct:F1}%";
    }

    [McpServerTool, Description(
        "List classic Brazilian derby (clássico) matches played in a given season across " +
        "all competitions: Fla-Flu, Gre-Nal, Majestoso, San-São, and more.")]
    public string Derbies([Description("Season year, e.g. 2023")] int season)
    {
        var derbies = _repo.Derbies(season).ToList();
        if (derbies.Count == 0) return $"No classic derby matches found in {season}.";
        var sb = new StringBuilder();
        sb.AppendLine($"Classic derbies in {season}:");
        foreach (var d in derbies)
        {
            sb.AppendLine($"{d.Name} ({d.Matches.Count} match(es)):");
            foreach (var m in d.Matches)
                sb.AppendLine($"  - {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition}{RoundOrStage(m)})");
        }
        return sb.ToString().TrimEnd();
    }

    // --------------------------------------------------------------- formatting

    private static string RoundOrStage(Match m)
    {
        var label = !string.IsNullOrEmpty(m.Stage) ? m.Stage
                    : !string.IsNullOrEmpty(m.Round) ? $"Round {m.Round}" : "";
        return label.Length == 0 ? "" : $", {label}";
    }

    private static string CompLabel(string? competition) =>
        string.IsNullOrWhiteSpace(competition) ? "" : $" [{competition}]";

    private static string NoMatches(string? team, string? opp, string? comp, int? season)
    {
        var parts = new List<string>();
        if (!string.IsNullOrEmpty(team)) parts.Add($"team '{team}'");
        if (!string.IsNullOrEmpty(opp)) parts.Add($"opponent '{opp}'");
        if (!string.IsNullOrEmpty(comp)) parts.Add($"competition '{comp}'");
        if (season is not null) parts.Add($"season {season}");
        var what = parts.Count == 0 ? "matches" : string.Join(", ", parts);
        return $"No matches found for {what}. Check the team/competition spelling or season.";
    }

    private static string NoPlayers(string? name, string? nat, string? club, string? pos, int? minOverall)
    {
        var parts = new List<string>();
        if (!string.IsNullOrEmpty(name)) parts.Add($"name '{name}'");
        if (!string.IsNullOrEmpty(nat)) parts.Add($"nationality '{nat}'");
        if (!string.IsNullOrEmpty(club)) parts.Add($"club '{club}'");
        if (!string.IsNullOrEmpty(pos)) parts.Add($"position '{pos}'");
        if (minOverall is not null) parts.Add($"min overall {minOverall}");
        return $"No players found matching {string.Join(", ", parts)}.";
    }

    private static string Pad(string s, int width) =>
        s.Length >= width ? s : s + new string(' ', width - s.Length);

    private static DateTime? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateTime.TryParse(s.AsSpan().Trim(), CultureInfo.InvariantCulture, DateTimeStyles.None, out var d)
            ? d : (DateTime?)null;
    }
}
