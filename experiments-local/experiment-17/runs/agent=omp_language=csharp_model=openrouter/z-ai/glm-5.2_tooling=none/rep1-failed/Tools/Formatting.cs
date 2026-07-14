// ============================================================================
// File: Tools/Formatting.cs
// ----------------------------------------------------------------------------
// Context: Shared text formatting helpers used by every MCP tool to render
// match lists, team records, and standings as the human-readable strings the
// MCP client returns to the LLM. Keeping the formatting here lets each tool
// stay a thin query-and-render layer.
// ============================================================================

using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tools;

internal static class Formatting
{
    public static string DateOnly(DateTime? d) =>
        d?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "????-??-??";

    /// <summary>Render one match as "DATE: Home X-Y Away (Competition Round/Stage)".</summary>
    public static string FormatMatch(SoccerMatch m)
    {
        var sb = new StringBuilder();
        sb.Append("- ").Append(DateOnly(m.Date)).Append(": ");
        sb.Append(m.HomeTeamRaw).Append(' ')
          .Append(m.HomeGoals?.ToString(CultureInfo.InvariantCulture) ?? "?")
          .Append('-')
          .Append(m.AwayGoals?.ToString(CultureInfo.InvariantCulture) ?? "?")
          .Append(' ').Append(m.AwayTeamRaw);

        sb.Append(" (").Append(m.Competition);
        if (!string.IsNullOrEmpty(m.Round)) sb.Append(" Round ").Append(m.Round);
        else if (!string.IsNullOrEmpty(m.Stage)) sb.Append(" ").Append(m.Stage);
        sb.Append(')');

        return sb.ToString();
    }

    public static string FormatRecord(TeamRecord r, string label)
    {
        var winRate = r.WinRate.ToString("P1", CultureInfo.InvariantCulture);
        return $"""
               {label}:
               - Matches: {r.Matches}
               - Wins: {r.Wins}, Draws: {r.Draws}, Losses: {r.Losses}
               - Goals For: {r.GoalsFor}, Goals Against: {r.GoalsAgainst}
               - Points: {r.Points} | Win rate: {winRate}
               """;
    }

    public static string FormatStandings(List<TeamRecord> standings, string title)
    {
        var sb = new StringBuilder();
        sb.AppendLine(title);
        int pos = 1;
        foreach (var r in standings)
        {
            var champ = pos == 1 ? " - Champion" : "";
            var relegated = pos > standings.Count - 4 ? " - Relegated" : "";
            sb.AppendLine(CultureInfo.InvariantCulture,
                $"{pos}. {r.Team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L, GF:{r.GoalsFor} GA:{r.GoalsAgainst}){champ}{relegated}");
            pos++;
        }
        return sb.ToString().TrimEnd();
    }
}
