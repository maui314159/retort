/*
 * Brazilian Soccer MCP Server - Response Formatter
 *
 * Converts query results into the human-readable formats shown in the
 * specification (standings, head-to-head, team records, player lists, etc.).
 */
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Queries;

public static class ResponseFormatter
{
    public static string FormatMatch(MatchRecord m)
    {
        var date = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown date";
        var home = m.HomeTeam;
        var away = m.AwayTeam;
        var score = m.HomeGoals.HasValue && m.AwayGoals.HasValue
            ? $"{m.HomeGoals}-{m.AwayGoals}"
            : "?-?";
        var extra = string.IsNullOrWhiteSpace(m.Round)
            ? (string.IsNullOrWhiteSpace(m.Stage) ? string.Empty : $" {m.Stage}")
            : $" Round {m.Round}";
        return $"{date}: {home} {score} {away} ({m.Competition}{extra})";
    }

    public static string FormatMatches(string title, IEnumerable<MatchRecord> matches)
    {
        var list = matches.ToList();
        if (list.Count == 0) return $"No matches found for: {title}";

        var lines = new List<string> { title };
        lines.AddRange(list.Select(m => $"- {FormatMatch(m)}"));
        return string.Join("\n", lines);
    }

    public static string FormatTeamStatistics(TeamStatistics stats)
    {
        return $"{stats.Team} record:\n" +
            $"- Matches: {stats.Matches}\n" +
            $"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}\n" +
            $"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}\n" +
            $"- Points: {stats.Points}\n" +
            $"- Win rate: {stats.WinRate:P1}";
    }

    public static string FormatHeadToHead(HeadToHeadRecord h2h)
    {
        return $"{h2h.TeamA} vs {h2h.TeamB} head-to-head:\n" +
            $"- Matches: {h2h.Matches}\n" +
            $"- {h2h.TeamA} wins: {h2h.TeamAWins}\n" +
            $"- {h2h.TeamB} wins: {h2h.TeamBWins}\n" +
            $"- Draws: {h2h.Draws}\n" +
            $"- {h2h.TeamA} goals: {h2h.TeamAGoals}\n" +
            $"- {h2h.TeamB} goals: {h2h.TeamBGoals}";
    }

    public static string FormatStandings(int season, string competition, IReadOnlyList<StandingRow> standings)
    {
        if (standings.Count == 0)
            return $"No standings available for {competition} {season}.";

        var lines = new List<string> { $"{season} {competition} Final Standings (calculated from matches):" };
        int rank = 1;
        foreach (var row in standings)
        {
            var suffix = rank == 1 ? " - Champion" : string.Empty;
            lines.Add($"{rank}. {row.Team} - {row.Points} pts ({row.Wins}W, {row.Draws}D, {row.Losses}L){suffix}");
            rank++;
        }
        return string.Join("\n", lines);
    }

    public static string FormatPlayers(string title, IEnumerable<PlayerRecord> players)
    {
        var list = players.ToList();
        if (list.Count == 0) return $"No players found for: {title}";

        var lines = new List<string> { title };
        int rank = 1;
        foreach (var p in list)
        {
            lines.Add($"{rank}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}");
            rank++;
        }
        return string.Join("\n", lines);
    }

    public static string FormatBiggestWins(IEnumerable<MatchRecord> matches)
    {
        var list = matches.ToList();
        if (list.Count == 0) return "No decisive matches found.";

        var lines = new List<string> { "Biggest victories:" };
        int rank = 1;
        foreach (var m in list)
        {
            lines.Add($"{rank}. {FormatMatch(m)}");
            rank++;
        }
        return string.Join("\n", lines);
    }

    public static string FormatAverageGoals(double avg, string? competition = null)
    {
        var label = string.IsNullOrWhiteSpace(competition) ? "all competitions" : competition;
        return $"Average goals per match ({label}): {avg:F2}";
    }
}
