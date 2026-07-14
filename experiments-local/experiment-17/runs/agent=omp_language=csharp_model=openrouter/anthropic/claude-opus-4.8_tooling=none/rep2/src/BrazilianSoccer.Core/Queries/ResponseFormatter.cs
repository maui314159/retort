// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    ResponseFormatter.cs
// Project: BrazilianSoccer.Core
// Purpose: Render QueryService results as the human-readable text blocks shown
//          in the spec's "Example answer format" sections. The MCP tools return
//          these strings to the calling LLM.
// Notes:   Pure formatting; no data access. Uses InvariantCulture so percentages
//          and dates are stable regardless of host locale.
// =============================================================================

using System.Globalization;
using System.Text;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Formats query results into readable answer text.</summary>
public static class ResponseFormatter
{
    private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    private static string Date(Match m) => m.Date?.ToString("yyyy-MM-dd", Inv) ?? "unknown date";

    private static string RoundOrStage(Match m)
    {
        if (!string.IsNullOrWhiteSpace(m.Round))
            return $"{m.CompetitionName} Round {m.Round}";
        if (!string.IsNullOrWhiteSpace(m.Stage))
            return $"{m.CompetitionName} {m.Stage}";
        return m.CompetitionName;
    }

    public static string MatchLine(Match m)
        => $"{Date(m)}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({RoundOrStage(m)})";

    public static string FormatMatches(string title, IReadOnlyList<Match> matches, int show = 15)
    {
        if (matches.Count == 0)
            return $"{title}\nNo matches found in the dataset.";

        var sb = new StringBuilder();
        sb.Append(title).Append('\n');
        foreach (var m in matches.Take(show))
            sb.Append("- ").Append(MatchLine(m)).Append('\n');
        if (matches.Count > show)
            sb.Append($"- ... ({matches.Count - show} more matches in dataset)\n");
        return sb.ToString().TrimEnd();
    }

    public static string FormatHeadToHead(HeadToHead h2h, int showMatches = 10)
    {
        var sb = new StringBuilder();
        sb.Append($"{h2h.TeamA} vs {h2h.TeamB}:\n");
        if (h2h.TotalMatches == 0)
        {
            sb.Append("No matches between these teams in the dataset.");
            return sb.ToString();
        }
        foreach (var m in h2h.Matches.Take(showMatches))
            sb.Append("- ").Append(MatchLine(m)).Append('\n');
        if (h2h.Matches.Count > showMatches)
            sb.Append($"- ... ({h2h.Matches.Count - showMatches} more matches in dataset)\n");
        sb.Append('\n');
        sb.Append($"Head-to-head in dataset: {h2h.TeamA} {h2h.TeamAWins} wins, ")
          .Append($"{h2h.TeamB} {h2h.TeamBWins} wins, {h2h.Draws} draws\n");
        sb.Append($"Goals: {h2h.TeamA} {h2h.TeamAGoals}, {h2h.TeamB} {h2h.TeamBGoals}");
        return sb.ToString();
    }

    public static string FormatTeamRecord(TeamRecord r, string? context = null)
    {
        var header = context is null ? $"{r.Team} record:" : $"{r.Team} {context}:";
        return new StringBuilder()
            .Append(header).Append('\n')
            .Append($"- Matches: {r.Played}\n")
            .Append($"- Wins: {r.Wins}, Draws: {r.Draws}, Losses: {r.Losses}\n")
            .Append($"- Goals For: {r.GoalsFor}, Goals Against: {r.GoalsAgainst}\n")
            .Append($"- Win rate: {Pct(r.WinRate)}")
            .ToString();
    }

    public static string FormatStandings(string title, IReadOnlyList<StandingRow> rows, int show = 20)
    {
        if (rows.Count == 0)
            return $"{title}\nNo data available for this competition/season.";
        var sb = new StringBuilder();
        sb.Append(title).Append('\n');
        foreach (var row in rows.Take(show))
        {
            var r = row.Record;
            var marker = row.Position == 1 ? " - Champion" : string.Empty;
            sb.Append($"{row.Position}. {r.Team} - {r.Points} pts ")
              .Append($"({r.Wins}W, {r.Draws}D, {r.Losses}L, GD {r.GoalDifference:+0;-0;0}){marker}\n");
        }
        return sb.ToString().TrimEnd();
    }

    public static string FormatPlayers(string title, IReadOnlyList<Player> players, int show = 25)
    {
        if (players.Count == 0)
            return $"{title}\nNo players found in the dataset.";
        var sb = new StringBuilder();
        sb.Append(title).Append('\n');
        var rank = 1;
        foreach (var p in players.Take(show))
        {
            var club = string.IsNullOrWhiteSpace(p.Club) ? "Free agent" : p.Club;
            sb.Append($"{rank}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {club}\n");
            rank++;
        }
        if (players.Count > show)
            sb.Append($"... ({players.Count - show} more players)\n");
        return sb.ToString().TrimEnd();
    }

    public static string FormatPlayer(Player p)
        => new StringBuilder()
            .Append($"{p.Name}\n")
            .Append($"- Nationality: {p.Nationality}\n")
            .Append($"- Age: {p.Age}\n")
            .Append($"- Overall: {p.Overall} (Potential: {p.Potential})\n")
            .Append($"- Position: {p.Position}\n")
            .Append($"- Club: {(string.IsNullOrWhiteSpace(p.Club) ? "Free agent" : p.Club)}\n")
            .Append($"- Preferred foot: {p.PreferredFoot}")
            .ToString();

    public static string FormatStatistics(string title, MatchStatistics s)
        => new StringBuilder()
            .Append(title).Append('\n')
            .Append($"- Matches: {s.TotalMatches}\n")
            .Append($"- Total goals: {s.TotalGoals}\n")
            .Append($"- Average goals per match: {s.AverageGoalsPerMatch.ToString("0.00", Inv)}\n")
            .Append($"- Home win rate: {Pct(s.HomeWinRate)}\n")
            .Append($"- Away win rate: {Pct(s.AwayWinRate)}\n")
            .Append($"- Draw rate: {Pct(s.DrawRate)}")
            .ToString();

    public static string FormatBiggestWins(string title, IReadOnlyList<Match> matches)
    {
        if (matches.Count == 0)
            return $"{title}\nNo matches found in the dataset.";
        var sb = new StringBuilder();
        sb.Append(title).Append('\n');
        var rank = 1;
        foreach (var m in matches)
            sb.Append($"{rank++}. {MatchLine(m)}\n");
        return sb.ToString().TrimEnd();
    }

    public static string FormatTopScorers(string title, IReadOnlyList<(string Team, int Goals)> teams)
    {
        if (teams.Count == 0)
            return $"{title}\nNo data available.";
        var sb = new StringBuilder();
        sb.Append(title).Append('\n');
        var rank = 1;
        foreach (var (team, goals) in teams)
            sb.Append($"{rank++}. {team} - {goals} goals\n");
        return sb.ToString().TrimEnd();
    }

    private static string Pct(double ratio)
        => (ratio * 100).ToString("0.0", Inv) + "%";
}
