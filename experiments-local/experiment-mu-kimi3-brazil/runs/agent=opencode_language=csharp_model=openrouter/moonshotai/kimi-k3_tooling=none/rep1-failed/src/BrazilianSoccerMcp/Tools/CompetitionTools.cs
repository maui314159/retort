using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// MCP tools answering questions about competitions and aggregate statistics
/// (categories 4 and 5 of the spec).
/// </summary>
[McpServerToolType]
public sealed class CompetitionTools
{
    private readonly SoccerDataService _data;
    public CompetitionTools(SoccerDataService data) => _data = data;

    [McpServerTool(Name = "get_standings"),
     Description("Compute a league table (points, W/D/L, goals) for a competition and season " +
                 "from match results, using 3 points for a win. " +
                 "Example: 'Who won the 2019 Brasileirão?' -> competition='Brasileirão', season=2019, " +
                 "the first row is the champion. Also shows relegation zone (bottom 4) for 20-team leagues.")]
    public string GetStandings(
        [Description("Competition, e.g. 'Brasileirão', 'Serie B'")] string competition,
        [Description("Season year, e.g. 2019")] int season,
        [Description("Max rows to return (default 20)")] int limit = 20)
    {
        var rows = _data.GetStandings(competition, season);
        if (rows.Count == 0)
            return $"No matches found for '{competition}' in season {season}.";

        var sb = new StringBuilder($"{season} {competition} standings (calculated from matches):\n");
        foreach (var r in rows.Take(limit))
        {
            var tag = r.Position == 1 ? " - Champion"
                : rows.Count >= 16 && r.Position > rows.Count - 4 ? " - Relegated" : "";
            sb.AppendLine($"{r.Position}. {r.Team} - {r.Points} pts " +
                          $"({r.Wins}W, {r.Draws}D, {r.Losses}L, " +
                          $"{r.GoalsFor} GF / {r.GoalsAgainst} GA){tag}");
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_overview_stats"),
     Description("Aggregate statistics: matches played, average goals per match, home win rate, " +
                 "draw rate, away win rate. Optionally filtered by competition and season. " +
                 "Example: 'What's the average goals per match in the Brasileirão?'")]
    public string GetOverviewStats(
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year (optional)")] int? season = null)
    {
        var s = _data.GetOverview(competition, season);
        if (s.MatchCount == 0) return "No matches found for the given filters.";

        var scope = competition ?? "All competitions";
        if (season is not null) scope += $" ({season})";
        var sb = new StringBuilder($"{scope}:\n");
        sb.AppendLine($"- Matches analyzed: {s.MatchCount}");
        sb.AppendLine($"- Total goals: {s.TotalGoals}");
        sb.AppendLine($"- Average goals per match: {s.AvgGoalsPerMatch:F2}");
        sb.AppendLine($"- Home win rate: {s.HomeWinRate:F1}%");
        sb.AppendLine($"- Draw rate: {s.DrawRate:F1}%");
        sb.AppendLine($"- Away win rate: {s.AwayWinRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool(Name = "get_biggest_wins"),
     Description("List the biggest victories (largest goal margin) in the dataset, " +
                 "optionally filtered by competition and season.")]
    public string GetBiggestWins(
        [Description("Competition filter (optional)")] string? competition = null,
        [Description("Season year (optional)")] int? season = null,
        [Description("Max results (default 10)")] int limit = 10)
    {
        var games = _data.GetBiggestWins(competition, season, limit);
        if (games.Count == 0) return "No matches found for the given filters.";

        var scope = competition ?? "all competitions";
        if (season is not null) scope += $" ({season})";
        var sb = new StringBuilder($"Biggest victories in {scope} (provided data):\n");
        var i = 1;
        foreach (var m in games)
        {
            sb.AppendLine($"{i}. {m}");
            i++;
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "list_competitions"),
     Description("List every competition available in the dataset.")]
    public string ListCompetitions()
    {
        var comps = _data.GetCompetitions();
        var sb = new StringBuilder("Competitions in dataset:\n");
        foreach (var c in comps)
        {
            var count = _data.Matches.Count(m => m.Competition == c);
            sb.AppendLine($"- {c} ({count} matches)");
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_knockout_bracket"),
     Description("Show knockout-stage matches (round of 16, quarterfinals, semifinals, final) " +
                 "of a cup competition and season, ordered by stage. " +
                 "Example: 'Show the 2018 Copa Libertadores bracket'.")]
    public string GetKnockoutBracket(
        [Description("Cup competition, e.g. 'Copa Libertadores' or 'Copa do Brasil'")] string competition,
        [Description("Season year, e.g. 2018")] int season)
    {
        var stages = new[] { "final", "semifinal", "quarterfinal", "round of 16", "oitavas", "quartas", "semi" };
        var games = _data.FindMatches(null, null, competition, season, null, null, 500)
            .Where(m => m.Round is not null &&
                        stages.Any(s => m.Round.Contains(s, StringComparison.OrdinalIgnoreCase)))
            .ToList();
        if (games.Count == 0)
            return $"No knockout matches found for '{competition}' in {season}.";

        static int StageOrder(string? round)
        {
            var r = (round ?? "").ToLowerInvariant();
            if (r.Contains("round of 16") || r.Contains("oitavas")) return 0;
            if (r.Contains("quarter") || r.Contains("quartas")) return 1;
            if (r.Contains("semi")) return 2;
            if (r.Contains("final")) return 3;
            return 4;
        }

        var sb = new StringBuilder($"{season} {competition} knockout bracket:\n");
        foreach (var g in games.OrderBy(m => StageOrder(m.Round)).ThenBy(m => m.Date))
            sb.AppendLine($"- [{g.Round}] {g.Date:yyyy-MM-dd}: {g.HomeTeam} {g.HomeGoals}-{g.AwayGoals} {g.AwayTeam}");
        return sb.ToString();
    }
}
