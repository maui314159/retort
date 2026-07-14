// -----------------------------------------------------------------------------
// File: Queries/ResponseFormatter.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Turns the structured query results into the human-readable text blocks shown
//   in TASK.md's "Example answer format" sections. The MCP tools return these
//   strings directly to the LLM, so formatting lives here (in Core) where it can
//   be unit-tested rather than buried in the transport layer.
//
//   Formatting rules mirror the spec examples: matches render as
//   "YYYY-MM-DD: Home H-A Away (Competition Round N)"; records show W/D/L, goals,
//   and a win-rate percentage; standings list "Pos. Team - pts (W D L)".
//   Percentages use one decimal; dates use ISO (yyyy-MM-dd). Everything is
//   culture-invariant.
// -----------------------------------------------------------------------------

using System.Globalization;
using System.Text;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Renders query results as the text answers described in the spec.</summary>
public static class ResponseFormatter
{
    private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    /// <summary>One match line, e.g. "2023-09-03: Flamengo-RJ 2-1 Fluminense-RJ (Brasileirão Série A, Round 22)".</summary>
    public static string MatchLine(Match m)
    {
        var sb = new StringBuilder();
        sb.Append(m.Date is { } d ? d.ToString("yyyy-MM-dd", Inv) : "date unknown");
        sb.Append(": ");
        sb.Append(m.HomeTeam);
        sb.Append(' ');
        sb.Append(m.HasResult ? $"{m.HomeGoals}-{m.AwayGoals}" : "vs");
        sb.Append(' ');
        sb.Append(m.AwayTeam);

        sb.Append(" (");
        sb.Append(Competitions.DisplayName(m.Competition));
        if (!string.IsNullOrWhiteSpace(m.Stage))
        {
            sb.Append(", ");
            sb.Append(m.Stage);
        }
        else if (!string.IsNullOrWhiteSpace(m.Round))
        {
            sb.Append(", Round ");
            sb.Append(m.Round);
        }
        sb.Append(')');
        return sb.ToString();
    }

    /// <summary>A bulleted list of matches with a header and optional cap notice.</summary>
    public static string MatchList(string header, IReadOnlyList<Match> matches, int show = 20)
    {
        if (matches.Count == 0)
            return $"{header}\nNo matches found in the dataset.";

        var sb = new StringBuilder();
        sb.Append(header).Append('\n');
        int n = Math.Min(show, matches.Count);
        for (int i = 0; i < n; i++)
            sb.Append("- ").Append(MatchLine(matches[i])).Append('\n');
        if (matches.Count > n)
            sb.Append($"- ... ({matches.Count - n} more in dataset)\n");
        return sb.ToString().TrimEnd('\n');
    }

    /// <summary>Head-to-head block matching the spec's Fla-Flu example.</summary>
    public static string HeadToHead(HeadToHead h, int show = 10)
    {
        var sb = new StringBuilder();
        sb.Append($"{h.TeamA} vs {h.TeamB} head-to-head:\n");
        if (h.TotalMatches == 0)
        {
            sb.Append("No matches found between these teams in the dataset.");
            return sb.ToString();
        }

        int n = Math.Min(show, h.Matches.Count);
        for (int i = 0; i < n; i++)
            sb.Append("- ").Append(MatchLine(h.Matches[i])).Append('\n');
        if (h.Matches.Count > n)
            sb.Append($"- ... ({h.Matches.Count - n} more in dataset)\n");

        sb.Append($"\nHead-to-head in dataset: {h.TeamA} {h.TeamAWins} wins, ");
        sb.Append($"{h.TeamB} {h.TeamBWins} wins, {h.Draws} draws ");
        sb.Append($"(goals {h.TeamAGoals}-{h.TeamBGoals}).");
        return sb.ToString();
    }

    /// <summary>Team record block, e.g. the Corinthians home-record example.</summary>
    public static string Record(TeamRecord r, string? scope = null)
    {
        var sb = new StringBuilder();
        sb.Append(r.Team);
        if (!string.IsNullOrWhiteSpace(scope))
            sb.Append(' ').Append(scope);
        sb.Append(":\n");
        sb.Append($"- Matches: {r.Played}\n");
        sb.Append($"- Wins: {r.Wins}, Draws: {r.Draws}, Losses: {r.Losses}\n");
        sb.Append($"- Goals For: {r.GoalsFor}, Goals Against: {r.GoalsAgainst} (GD {r.GoalDifference:+0;-0;0})\n");
        sb.Append($"- Points: {r.Points}\n");
        sb.Append($"- Win rate: {Percent(r.WinRate)}");
        return sb.ToString();
    }

    /// <summary>Full or top-N calculated standings table.</summary>
    public static string StandingsTable(Standings s, int show = 20)
    {
        if (s.Rows.Count == 0)
            return $"No {Competitions.DisplayName(s.Competition)} {s.Season} matches found in the dataset.";

        var sb = new StringBuilder();
        sb.Append($"{s.Season} {Competitions.DisplayName(s.Competition)} table (calculated from matches):\n");
        int n = Math.Min(show, s.Rows.Count);
        for (int i = 0; i < n; i++)
        {
            var r = s.Rows[i].Record;
            sb.Append($"{s.Rows[i].Position}. {r.Team} - {r.Points} pts ");
            sb.Append($"({r.Wins}W {r.Draws}D {r.Losses}L, GD {r.GoalDifference:+0;-0;0})");
            if (i == 0)
                sb.Append(" - Champion");
            sb.Append('\n');
        }
        if (s.Rows.Count > n)
            sb.Append($"... ({s.Rows.Count - n} more teams)\n");
        return sb.ToString().TrimEnd('\n');
    }

    /// <summary>Aggregate statistics block.</summary>
    public static string Summary(string header, MatchStatsSummary s)
    {
        var sb = new StringBuilder();
        sb.Append(header).Append(":\n");
        sb.Append($"- Matches (decided): {s.MatchesWithResult}\n");
        sb.Append($"- Total goals: {s.TotalGoals}\n");
        sb.Append($"- Average goals per match: {s.AverageGoalsPerMatch.ToString("0.00", Inv)}\n");
        sb.Append($"- Home win rate: {Percent(s.HomeWinRate)}\n");
        sb.Append($"- Away win rate: {Percent(s.AwayWinRate)}\n");
        sb.Append($"- Draw rate: {Percent(s.DrawRate)}");
        return sb.ToString();
    }

    /// <summary>A numbered list of players, spec "Top-rated players" style.</summary>
    public static string PlayerList(string header, IReadOnlyList<Player> players, int show = 20)
    {
        if (players.Count == 0)
            return $"{header}\nNo players found in the dataset.";

        var sb = new StringBuilder();
        sb.Append(header).Append('\n');
        int n = Math.Min(show, players.Count);
        for (int i = 0; i < n; i++)
            sb.Append($"{i + 1}. ").Append(PlayerLine(players[i])).Append('\n');
        if (players.Count > n)
            sb.Append($"... ({players.Count - n} more in dataset)\n");
        return sb.ToString().TrimEnd('\n');
    }

    /// <summary>One player line, e.g. "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain (Brazil)".</summary>
    public static string PlayerLine(Player p)
    {
        var sb = new StringBuilder();
        sb.Append(p.Name);
        if (p.Overall is not null)
            sb.Append($" - Overall: {p.Overall}");
        if (p.Potential is not null)
            sb.Append($", Potential: {p.Potential}");
        if (!string.IsNullOrWhiteSpace(p.Position))
            sb.Append($", Position: {p.Position}");
        if (!string.IsNullOrWhiteSpace(p.Club))
            sb.Append($", Club: {p.Club}");
        sb.Append($" ({p.Nationality}");
        if (p.Age is not null)
            sb.Append($", age {p.Age}");
        sb.Append(')');
        return sb.ToString();
    }

    /// <summary>Club breakdown block, "Flamengo: 8 players (avg rating: 74)".</summary>
    public static string ClubBreakdown(string header, IReadOnlyList<ClubPlayers> clubs, int show = 15)
    {
        if (clubs.Count == 0)
            return $"{header}\nNo clubs found for that filter.";

        var sb = new StringBuilder();
        sb.Append(header).Append('\n');
        int n = Math.Min(show, clubs.Count);
        for (int i = 0; i < n; i++)
        {
            var c = clubs[i];
            sb.Append($"- {c.Club}: {c.Count} players (avg rating: {c.AverageOverall.ToString("0", Inv)})\n");
        }
        if (clubs.Count > n)
            sb.Append($"- ... ({clubs.Count - n} more clubs)\n");
        return sb.ToString().TrimEnd('\n');
    }

    private static string Percent(double fraction)
        => (fraction * 100).ToString("0.0", Inv) + "%";
}
