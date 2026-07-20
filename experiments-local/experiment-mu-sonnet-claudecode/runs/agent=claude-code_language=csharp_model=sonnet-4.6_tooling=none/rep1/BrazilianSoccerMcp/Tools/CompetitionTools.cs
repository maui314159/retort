using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public class CompetitionTools(SoccerDataService dataService)
{
    [McpServerTool(Name = "get_standings"), Description(
        "Get Brasileirão standings for a given season, calculated from match results. " +
        "Shows position, team, played, wins, draws, losses, goals, points.")]
    public string GetStandings(
        [Description("Season year (e.g., 2019, 2022, 2023)")]
        int season)
    {
        var standings = dataService.GetBrasileiraStandings(season);

        if (standings.Count == 0)
            return $"No Brasileirão standings data available for season {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"Brasileirão {season} Standings (calculated from match data):");
        sb.AppendLine($"{"Pos",-4} {"Team",-30} {"P",-4} {"W",-4} {"D",-4} {"L",-4} {"GF",-4} {"GA",-4} {"GD",-5} {"Pts",-4}");
        sb.AppendLine(new string('-', 75));

        for (int i = 0; i < standings.Count; i++)
        {
            var e = standings[i];
            var gd = e.GoalDifference >= 0 ? $"+{e.GoalDifference}" : e.GoalDifference.ToString();
            sb.AppendLine($"{i + 1,-4} {e.Team,-30} {e.Played,-4} {e.Wins,-4} {e.Draws,-4} {e.Losses,-4} {e.GoalsFor,-4} {e.GoalsAgainst,-4} {gd,-5} {e.Points,-4}");
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool(Name = "find_cup_matches"), Description(
        "Find Copa do Brasil or Copa Libertadores matches. Can filter by team, season, and stage.")]
    public string FindCupMatches(
        [Description("Which cup: 'copa do brasil' or 'libertadores'")]
        string cup,
        [Description("Team name to filter by (optional)")]
        string? team = null,
        [Description("Season year (optional)")]
        int? season = null,
        [Description("Stage/round name e.g. 'final', 'semi-final', 'group stage' (optional)")]
        string? stage = null,
        [Description("Maximum results (default 30)")]
        int limit = 30)
    {
        limit = Math.Clamp(limit, 1, 200);
        var matches = dataService.FindMatches(team, season: season, competition: cup, limit: limit);

        if (!string.IsNullOrWhiteSpace(stage))
        {
            matches = matches
                .Where(m => (m.Stage ?? m.Round ?? "").Contains(stage, StringComparison.OrdinalIgnoreCase))
                .Take(limit)
                .ToList();
        }

        if (matches.Count == 0)
            return $"No matches found for {cup}{(team != null ? $" involving {team}" : "")}{(season != null ? $" in {season}" : "")}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{cup.ToUpper()} matches ({matches.Count} results):");
        foreach (var m in matches)
        {
            var dateStr = m.DateTime?.ToString("yyyy-MM-dd") ?? "unknown";
            var extra = m.Stage ?? m.Round ?? "";
            sb.AppendLine($"  {dateStr}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} | Season {m.Season}{(extra != "" ? $" | {extra}" : "")}");
        }
        return sb.ToString().TrimEnd();
    }
}
