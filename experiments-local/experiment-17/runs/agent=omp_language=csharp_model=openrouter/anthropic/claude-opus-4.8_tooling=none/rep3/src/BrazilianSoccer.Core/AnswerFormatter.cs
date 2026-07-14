// =============================================================================
// File:    AnswerFormatter.cs
// Project: BrazilianSoccer.Core
// Purpose: Render query-engine results into the human-readable text blocks the
//          MCP tools return, mirroring the "Example answer format" sections in
//          TASK.md (match lists with head-to-head footer, team records, player
//          rankings, league standings, statistics summaries).
// Context: Kept separate from SoccerDatabase so the engine stays pure data and
//          the server layer (Tools.cs) just calls a formatter. Dates print as
//          ISO (yyyy-MM-dd); unknown dates show "????-??-??". All output is
//          UTF-8 and preserves Portuguese accents.
// =============================================================================

using System.Globalization;
using System.Text;

namespace BrazilianSoccer.Core;

public static class AnswerFormatter
{
    private static string D(DateTime? dt) => dt?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "????-??-??";

    public static string Score(Match m) =>
        m.HasScore ? $"{m.HomeGoals}-{m.AwayGoals}" : "?-?";

    public static string MatchLine(Match m)
    {
        var sb = new StringBuilder();
        sb.Append(D(m.Date)).Append(": ")
          .Append(m.HomeTeam).Append(' ').Append(Score(m)).Append(' ').Append(m.AwayTeam)
          .Append(" (").Append(m.Competition.DisplayName());
        if (!string.IsNullOrEmpty(m.Round)) sb.Append(" Round ").Append(m.Round);
        else if (!string.IsNullOrEmpty(m.Stage)) sb.Append(" - ").Append(m.Stage);
        sb.Append(')');
        return sb.ToString();
    }

    public static string Matches(IReadOnlyList<Match> matches, int show = 25, string? title = null)
    {
        if (matches.Count == 0) return "No matches found.";
        var sb = new StringBuilder();
        if (title is not null) sb.AppendLine(title);
        int n = Math.Min(show, matches.Count);
        for (int i = 0; i < n; i++) sb.Append("- ").AppendLine(MatchLine(matches[i]));
        if (matches.Count > n) sb.AppendLine($"- ... ({matches.Count - n} more matches in dataset)");
        return sb.ToString().TrimEnd();
    }

    public static string HeadToHead(HeadToHead h, int show = 10)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"{h.TeamA} vs {h.TeamB}:");
        int n = Math.Min(show, h.Matches.Count);
        for (int i = 0; i < n; i++) sb.Append("- ").AppendLine(MatchLine(h.Matches[i]));
        if (h.Matches.Count > n) sb.AppendLine($"- ... ({h.Matches.Count - n} more matches in dataset)");
        sb.AppendLine();
        sb.AppendLine($"Head-to-head in dataset: {h.TeamA} {h.TeamAWins} wins, " +
                      $"{h.TeamB} {h.TeamBWins} wins, {h.Draws} draws " +
                      $"(goals {h.TeamAGoals}-{h.TeamBGoals}).");
        return sb.ToString().TrimEnd();
    }

    public static string TeamRecord(TeamRecord r, string context)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"{r.Team} {context}:");
        sb.AppendLine($"- Matches: {r.Played}");
        sb.AppendLine($"- Wins: {r.Wins}, Draws: {r.Draws}, Losses: {r.Losses}");
        sb.AppendLine($"- Goals For: {r.GoalsFor}, Goals Against: {r.GoalsAgainst}");
        sb.Append($"- Win rate: {r.WinRate * 100:0.0}%");
        return sb.ToString();
    }

    public static string Players(IReadOnlyList<Player> players, string title, int show = 25)
    {
        if (players.Count == 0) return "No players found.";
        var sb = new StringBuilder();
        sb.AppendLine(title);
        int n = Math.Min(show, players.Count);
        for (int i = 0; i < n; i++)
        {
            var p = players[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall}, " +
                          $"Position: {(string.IsNullOrEmpty(p.Position) ? "?" : p.Position)}, " +
                          $"Club: {(string.IsNullOrEmpty(p.Club) ? "Free agent" : p.Club)}" +
                          $"{(string.IsNullOrEmpty(p.Nationality) ? "" : $" [{p.Nationality}]")}");
        }
        if (players.Count > n) sb.AppendLine($"... ({players.Count - n} more players)");
        return sb.ToString().TrimEnd();
    }

    public static string Standings(IReadOnlyList<Standing> table, Competition comp, int season, int show = 30)
    {
        if (table.Count == 0) return $"No standings available for {comp.DisplayName()} {season}.";
        var sb = new StringBuilder();
        sb.AppendLine($"{season} {comp.DisplayName()} Final Standings (calculated from matches):");
        int n = Math.Min(show, table.Count);
        for (int i = 0; i < n; i++)
        {
            var s = table[i];
            var r = s.Record;
            var tag = i == 0 ? " - Champion" : "";
            sb.AppendLine($"{s.Position}. {r.Team} - {r.Points} pts " +
                          $"({r.Wins}W, {r.Draws}D, {r.Losses}L, GD {r.GoalDifference:+0;-0;0}){tag}");
        }
        return sb.ToString().TrimEnd();
    }

    public static string GoalStats(int matches, double avg, double homeWinRate, string context)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Statistics {context}:");
        sb.AppendLine($"- Matches with scores: {matches}");
        sb.AppendLine($"- Average goals per match: {avg:0.00}");
        sb.Append($"- Home win rate: {homeWinRate * 100:0.0}%");
        return sb.ToString();
    }

    public static string TeamRanking(IReadOnlyList<TeamRecord> records, string title)
    {
        if (records.Count == 0) return "No teams found.";
        var sb = new StringBuilder();
        sb.AppendLine(title);
        for (int i = 0; i < records.Count; i++)
        {
            var r = records[i];
            sb.AppendLine($"{i + 1}. {r.Team} - {r.WinRate * 100:0.0}% " +
                          $"({r.Wins}W, {r.Draws}D, {r.Losses}L in {r.Played}, GD {r.GoalDifference:+0;-0;0})");
        }
        return sb.ToString().TrimEnd();
    }
}
