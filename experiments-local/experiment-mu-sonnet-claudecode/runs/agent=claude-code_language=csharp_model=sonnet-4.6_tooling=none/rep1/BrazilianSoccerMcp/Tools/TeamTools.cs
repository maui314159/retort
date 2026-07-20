using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public class TeamTools(SoccerDataService dataService)
{
    [McpServerTool(Name = "get_team_stats"), Description(
        "Get statistics for a team: wins, losses, draws, goals scored/conceded, win rate. " +
        "Can filter by season and/or competition.")]
    public string GetTeamStats(
        [Description("Team name (e.g., 'Corinthians', 'Flamengo')")]
        string team,
        [Description("Season year (e.g., 2022). Omit for all-time stats.")]
        int? season = null,
        [Description("Competition: 'brasileirao', 'copa do brasil', 'libertadores'. Omit for all competitions.")]
        string? competition = null)
    {
        var stats = dataService.GetTeamStats(team, season, competition);

        if (stats.Played == 0)
        {
            var filters = season != null || competition != null
                ? $" in {competition ?? "all competitions"}{(season != null ? $" {season}" : "")}"
                : "";
            return $"No matches found for '{team}'{filters}.";
        }

        var sb = new StringBuilder();
        var header = competition != null
            ? $"{team} - {competition}{(season != null ? $" {season}" : "")}"
            : $"{team}{(season != null ? $" {season}" : "")} (all competitions)";

        sb.AppendLine(header);
        sb.AppendLine($"Matches Played: {stats.Played}");
        sb.AppendLine($"Record: {stats.Wins}W - {stats.Draws}D - {stats.Losses}L");
        sb.AppendLine($"Points: {stats.Points}");
        sb.AppendLine($"Goals: {stats.GoalsFor} scored, {stats.GoalsAgainst} conceded (diff: {stats.GoalDifference:+#;-#;0})");
        sb.AppendLine($"Win Rate: {stats.WinRate:F1}%");

        return sb.ToString().TrimEnd();
    }

    [McpServerTool(Name = "compare_teams"), Description(
        "Compare two teams head-to-head: match history, win/draw/loss record, goals scored.")]
    public string CompareTeams(
        [Description("First team name (e.g., 'Palmeiras')")]
        string team1,
        [Description("Second team name (e.g., 'Santos')")]
        string team2,
        [Description("Season year to filter by. Omit for all-time.")]
        int? season = null)
    {
        var h2h = dataService.GetHeadToHead(team1, team2);

        if (h2h.TotalMatches == 0)
            return $"No head-to-head matches found between '{team1}' and '{team2}'.";

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-Head: {team1} vs {team2}");
        sb.AppendLine($"Total Matches: {h2h.TotalMatches}");
        sb.AppendLine($"{team1}: {h2h.Team1Wins} wins | Draws: {h2h.Draws} | {team2}: {h2h.Team2Wins} wins");
        sb.AppendLine($"Goals: {team1} {h2h.Team1Goals} - {h2h.Team2Goals} {team2}");
        sb.AppendLine();

        var recent = season.HasValue
            ? h2h.Matches.Where(m => m.Season == season.Value).Take(10).ToList()
            : h2h.Matches.Take(10).ToList();

        if (recent.Count > 0)
        {
            sb.AppendLine($"Most recent {recent.Count} match(es):");
            foreach (var m in recent)
            {
                var dateStr = m.DateTime?.ToString("yyyy-MM-dd") ?? "unknown";
                sb.AppendLine($"  {dateStr}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})");
            }
        }

        return sb.ToString().TrimEnd();
    }
}
