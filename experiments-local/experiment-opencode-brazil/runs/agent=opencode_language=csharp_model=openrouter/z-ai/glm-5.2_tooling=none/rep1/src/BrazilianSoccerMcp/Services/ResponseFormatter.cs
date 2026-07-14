// Context block
// File: Services/ResponseFormatter.cs
// Purpose: Turn service results into the human-readable answer formats described in
// TASK.md for the Brazilian Soccer MCP server. Each formatter mirrors an example answer
// block (match listings with head-to-head tally, team record blocks, player rankings,
// computed standings, and biggest-wins summaries). The output is plain text intended to
// be embedded directly into an LLM answer. Keeping formatting separate from query logic
// lets the MCP tools remain thin wrappers.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Formats query results as text answer blocks.</summary>
public sealed class ResponseFormatter
{
    public string FormatMatches(List<MatchRecord> matches, int max = 20)
    {
        if (matches.Count == 0)
        {
            return "No matches found.";
        }
        var sb = new StringBuilder();
        int shown = 0;
        foreach (var m in matches)
        {
            if (shown >= max) break;
            sb.AppendLine("- " + m.Summary);
            shown++;
        }
        if (matches.Count > max)
        {
            sb.AppendLine($"... ({matches.Count - max} more matches in dataset)");
        }
        return sb.ToString().TrimEnd();
    }

    public string FormatHeadToHead(HeadToHeadResult h2h, int max = 20)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"{h2h.TeamA} vs {h2h.TeamB}:");
        if (h2h.Matches.Count == 0)
        {
            sb.AppendLine("No matches found between these teams.");
            return sb.ToString().TrimEnd();
        }
        int shown = 0;
        foreach (var m in h2h.Matches)
        {
            if (shown >= max) break;
            sb.AppendLine("- " + m.Summary);
            shown++;
        }
        if (h2h.Matches.Count > max)
        {
            sb.AppendLine($"... ({h2h.Matches.Count - max} more matches in dataset)");
        }
        sb.AppendLine();
        sb.AppendLine($"Head-to-head in dataset: {h2h.TeamA} {h2h.TeamAWins} wins, " +
            $"{h2h.TeamB} {h2h.TeamBWins} wins, {h2h.Draws} draws");
        return sb.ToString().TrimEnd();
    }

    public string FormatTeamStats(TeamStats stats)
    {
        var venueLabel = stats.Venue switch
        {
            Venue.Home => " home",
            Venue.Away => " away",
            _ => "",
        };
        var seasonLabel = stats.Season is null ? "" : $" ({stats.Season})";
        var compLabel = stats.Competition is null ? "" : $" {stats.Competition}";
        var sb = new StringBuilder();
        sb.AppendLine($"{stats.Team}{venueLabel} record{seasonLabel}{compLabel}:");
        sb.AppendLine($"- Matches: {stats.Played}");
        sb.AppendLine($"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {stats.WinRate.ToString("0.0", CultureInfo.InvariantCulture)}%");
        return sb.ToString().TrimEnd();
    }

    public string FormatComparison(TeamComparison comp)
    {
        var sb = new StringBuilder();
        sb.AppendLine(FormatTeamStats(comp.TeamA));
        sb.AppendLine();
        sb.AppendLine(FormatTeamStats(comp.TeamB));
        sb.AppendLine();
        sb.AppendLine(FormatHeadToHead(comp.HeadToHead));
        return sb.ToString().TrimEnd();
    }

    public string FormatPlayers(List<PlayerRecord> players, string title)
    {
        if (players.Count == 0)
        {
            return title + ": no players found.";
        }
        var sb = new StringBuilder();
        sb.AppendLine(title + ":");
        int rank = 1;
        foreach (var p in players)
        {
            sb.AppendLine($"{rank}. {p.Display}");
            rank++;
        }
        return sb.ToString().TrimEnd();
    }

    public string FormatClubCounts(List<ClubPlayerCount> clubs, string title)
    {
        if (clubs.Count == 0)
        {
            return title + ": no data found.";
        }
        var sb = new StringBuilder();
        sb.AppendLine(title + ":");
        foreach (var c in clubs)
        {
            sb.AppendLine($"- {c.Club}: {c.Count} players (avg rating: {c.AverageOverall.ToString("0", CultureInfo.InvariantCulture)})");
        }
        return sb.ToString().TrimEnd();
    }

    public string FormatStandings(List<StandingRow> rows, int season, int championOnly = 0)
    {
        if (rows.Count == 0)
        {
            return $"No standings available for season {season}.";
        }
        var sb = new StringBuilder();
        sb.AppendLine($"{season} Brasileirao Standings (calculated from matches):");
        int limit = championOnly > 0 ? championOnly : rows.Count;
        int i = 0;
        foreach (var r in rows)
        {
            if (i >= limit) break;
            var championTag = i == 0 ? " - Champion" : "";
            sb.AppendLine($"{r.Position}. {r.Team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L){championTag}");
            i++;
        }
        return sb.ToString().TrimEnd();
    }

    public string FormatBiggestWins(List<MatchRecord> wins, double avgGoals, OutcomeRates rates)
    {
        var sb = new StringBuilder();
        sb.AppendLine("Biggest victories in dataset:");
        int rank = 1;
        foreach (var m in wins)
        {
            var margin = Math.Abs(m.HomeGoal - m.AwayGoal);
            var winner = m.HomeGoal > m.AwayGoal ? m.HomeRaw : m.AwayRaw;
            var loser = m.HomeGoal > m.AwayGoal ? m.AwayRaw : m.HomeRaw;
            sb.AppendLine($"{rank}. {m.Date:yyyy-MM-dd}: {winner} {Math.Max(m.HomeGoal, m.AwayGoal)}-{Math.Min(m.HomeGoal, m.AwayGoal)} {loser} (margin {margin}, {m.CompetitionLabel})");
            rank++;
        }
        sb.AppendLine();
        sb.AppendLine($"Average goals per match: {avgGoals.ToString("0.00", CultureInfo.InvariantCulture)}");
        sb.AppendLine($"Home win rate: {rates.HomeWinRate.ToString("0.0", CultureInfo.InvariantCulture)}%");
        return sb.ToString().TrimEnd();
    }
}
