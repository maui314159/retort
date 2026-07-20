// BrazilianSoccerMcp.Core / Queries / ResultFormatter.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Renders the structured query results into
// the human-readable answer formats shown in TASK.md ("Example answer format"
// blocks under each Required Capability). The MCP tools expose these formatted
// strings so an LLM client gets pre-shaped prose to answer with, while still
// returning enough structure for callers that prefer to render themselves.
// Design: pure functions over result records — no data service dependency — so
// the formatter is trivially unit-testable.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Queries;

/// <summary>
/// Renders query results into the human-readable formats from TASK.md.
/// </summary>
public static class ResultFormatter
{
    public static string FormatMatchLine(Match m)
    {
        var date = m.Date?.ToString("yyyy-MM-dd") ?? "unknown date";
        var score = m.HasScore ? $"{m.HomeGoals}-{m.AwayGoals}" : "?-?";
        var comp = m.CompetitionLabel;
        var extra = !string.IsNullOrEmpty(m.Round) ? $" Round {m.Round}" :
                    !string.IsNullOrEmpty(m.Stage) ? $" ({m.Stage})" : "";
        var season = m.Season.HasValue ? $" {m.Season}" : "";
        return $"- {date}: {m.HomeTeamOriginal} {score} {m.AwayTeamOriginal} ({comp}{extra}{season})";
    }

    public static string FormatMatchesBetween(string teamA, string teamB, IReadOnlyList<Match> matches, HeadToHead? h2h = null)
    {
        if (matches.Count == 0)
            return $"No matches between {teamA} and {teamB} found in the dataset.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{teamA} vs {teamB}:");
        foreach (var m in matches)
            sb.AppendLine(FormatMatchLine(m));
        if (matches.Count > 20)
            sb.AppendLine($"... ({matches.Count - 20} more matches in dataset)");
        if (h2h is not null)
            sb.AppendLine().AppendLine($"Head-to-head in dataset: {h2h.TeamA} {h2h.TeamAWins} wins, {h2h.TeamB} {h2h.TeamBWins} wins, {h2h.Draws} draws");
        return sb.ToString().TrimEnd();
    }

    public static string FormatTeamRecord(string team, TeamRecord record, string? scope = null)
    {
        var heading = string.IsNullOrEmpty(scope)
            ? $"{team} record:"
            : $"{team} record ({scope}):";
        return $"{heading}\n" +
               $"- Matches: {record.Matches}\n" +
               $"- Wins: {record.Wins}, Draws: {record.Draws}, Losses: {record.Losses}\n" +
               $"- Goals For: {record.GoalsFor}, Goals Against: {record.GoalsAgainst}\n" +
               $"- Win rate: {(record.Matches == 0 ? 0 : record.WinRate * 100):F1}%";
    }

    public static string FormatStandings(IReadOnlyList<StandingsRow> table, string title)
    {
        if (table.Count == 0)
            return $"{title}: no scored matches in scope.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{title} (calculated from matches):");
        foreach (var row in table)
        {
            var champ = row.IsChampion ? " - Champion" : "";
            sb.AppendLine($"{row.Position}. {row.Team} - {row.Record.Points} pts " +
                          $"({row.Record.Wins}W, {row.Record.Draws}D, {row.Record.Losses}L)" +
                          $" (GF {row.Record.GoalsFor}, GA {row.Record.GoalsAgainst}){champ}");
        }
        return sb.ToString().TrimEnd();
    }

    public static string FormatBiggestWins(IReadOnlyList<BiggestWin> wins, string title)
    {
        if (wins.Count == 0)
            return $"{title}: no scored matches in scope.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{title}:");
        int i = 1;
        foreach (var w in wins)
        {
            var date = w.Date?.ToString("yyyy-MM-dd") ?? "unknown date";
            var season = w.Season.HasValue ? $" ({w.Competition} {w.Season})" : $" ({w.Competition})";
            sb.AppendLine($"{i++}. {date}: {w.Winner} {w.WinnerGoals}-{w.LoserGoals} {w.Loser}{season}");
        }
        return sb.ToString().TrimEnd();
    }

    public static string FormatTopPlayers(IReadOnlyList<Player> players, string title)
    {
        if (players.Count == 0)
            return $"{title}: no matching players in dataset.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{title}:");
        int i = 1;
        foreach (var p in players)
            sb.AppendLine($"{i++}. {p.Name} - Overall: {p.Overall}, Position: {p.Position ?? "?"}, Club: {p.Club ?? "?"}");
        return sb.ToString().TrimEnd();
    }

    public static string FormatBuckets(IReadOnlyList<PlayerBucket> buckets, string title)
    {
        if (buckets.Count == 0)
            return $"{title}: no matching players in dataset.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{title}:");
        foreach (var b in buckets)
            sb.AppendLine($"- {b.Label}: {b.Count} players (avg rating: {b.AverageRating:F0})");
        return sb.ToString().TrimEnd();
    }
}
