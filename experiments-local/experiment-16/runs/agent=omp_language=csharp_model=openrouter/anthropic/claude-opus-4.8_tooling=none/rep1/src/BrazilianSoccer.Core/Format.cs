// =============================================================================
// Context: Brazilian Soccer MCP Server — text formatting.
//
// Renders query-engine results into the human-readable layouts shown in the
// spec's "Example answer format" blocks (match lists with head-to-head summary,
// team records with win rate, ranked player lists, league standings, aggregate
// stats). Kept separate from both the engine (pure data) and the MCP layer
// (transport) so the same strings can be asserted in tests.
// =============================================================================
using System.Globalization;
using System.Text;

namespace BrazilianSoccer.Core;

public static class Format
{
    private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    public static string CompetitionLabel(Competition c) => c switch
    {
        Competition.BrasileiraoSerieA => "Brasileirão Série A",
        Competition.BrasileiraoSerieB => "Brasileirão Série B",
        Competition.BrasileiraoSerieC => "Brasileirão Série C",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Copa Libertadores",
        _ => "Other",
    };

    public static string MatchLine(Match m)
    {
        var date = m.Date?.ToString("yyyy-MM-dd", Inv) ?? "????-??-??";
        var score = m.HasResult ? $"{m.HomeGoal}-{m.AwayGoal}" : "vs";
        var sb = new StringBuilder();
        sb.Append(date).Append(": ")
          .Append(m.HomeTeam).Append(' ').Append(score).Append(' ').Append(m.AwayTeam)
          .Append(" (").Append(CompetitionLabel(m.Competition));
        if (!string.IsNullOrEmpty(m.Round))
            sb.Append(" Round ").Append(m.Round);
        else if (!string.IsNullOrEmpty(m.Stage))
            sb.Append(' ').Append(m.Stage);
        sb.Append(')');
        return sb.ToString();
    }

    public static string Matches(IReadOnlyList<Match> matches, string? title = null, int maxLines = 25)
    {
        if (matches.Count == 0)
            return title is null ? "No matches found." : $"{title}\nNo matches found.";

        var sb = new StringBuilder();
        if (title is not null) sb.AppendLine(title);

        int shown = Math.Min(matches.Count, maxLines);
        for (int i = 0; i < shown; i++)
            sb.Append("- ").AppendLine(MatchLine(matches[i]));
        if (matches.Count > shown)
            sb.Append("- ... (").Append(matches.Count - shown).AppendLine(" more matches in dataset)");
        return sb.ToString().TrimEnd();
    }

    public static string TeamRecord(TeamRecord r, string? heading = null)
    {
        var sb = new StringBuilder();
        sb.AppendLine(heading ?? $"{r.Team} record:");
        sb.Append("- Matches: ").Append(r.Matches).AppendLine();
        sb.Append("- Wins: ").Append(r.Wins)
          .Append(", Draws: ").Append(r.Draws)
          .Append(", Losses: ").Append(r.Losses).AppendLine();
        sb.Append("- Goals For: ").Append(r.GoalsFor)
          .Append(", Goals Against: ").Append(r.GoalsAgainst).AppendLine();
        sb.Append("- Points: ").Append(r.Points).AppendLine();
        sb.Append("- Win rate: ").Append((r.WinRate * 100).ToString("0.0", Inv)).Append('%');
        return sb.ToString();
    }

    public static string HeadToHead(HeadToHead h)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-head: {h.TeamA} vs {h.TeamB}");
        sb.Append("- Matches: ").Append(h.Matches).AppendLine();
        sb.Append("- ").Append(h.TeamA).Append(" wins: ").Append(h.TeamAWins).AppendLine();
        sb.Append("- ").Append(h.TeamB).Append(" wins: ").Append(h.TeamBWins).AppendLine();
        sb.Append("- Draws: ").Append(h.Draws).AppendLine();
        sb.Append("- Goals: ").Append(h.TeamA).Append(' ').Append(h.TeamAGoals)
          .Append(", ").Append(h.TeamB).Append(' ').Append(h.TeamBGoals);
        return sb.ToString();
    }

    public static string Players(IReadOnlyList<Player> players, string? title = null, int maxLines = 25)
    {
        if (players.Count == 0)
            return title is null ? "No players found." : $"{title}\nNo players found.";

        var sb = new StringBuilder();
        if (title is not null) sb.AppendLine(title);

        int shown = Math.Min(players.Count, maxLines);
        for (int i = 0; i < shown; i++)
        {
            var p = players[i];
            sb.Append(i + 1).Append(". ").Append(p.Name)
              .Append(" - Overall: ").Append(p.Overall?.ToString(Inv) ?? "?")
              .Append(", Position: ").Append(p.Position ?? "?")
              .Append(", Club: ").Append(p.Club ?? "?")
              .Append(", Nationality: ").Append(p.Nationality)
              .AppendLine();
        }
        if (players.Count > shown)
            sb.Append("... (").Append(players.Count - shown).AppendLine(" more)");
        return sb.ToString().TrimEnd();
    }

    public static string Standings(IReadOnlyList<StandingRow> rows, string title, int maxLines = 30)
    {
        if (rows.Count == 0)
            return $"{title}\nNo data available.";

        var sb = new StringBuilder();
        sb.AppendLine(title);
        int shown = Math.Min(rows.Count, maxLines);
        for (int i = 0; i < shown; i++)
        {
            var r = rows[i];
            var rec = r.Record;
            sb.Append(r.Position).Append(". ").Append(rec.Team)
              .Append(" - ").Append(rec.Points).Append(" pts (")
              .Append(rec.Wins).Append("W, ").Append(rec.Draws).Append("D, ").Append(rec.Losses).Append("L), GD ")
              .Append(rec.GoalDifference >= 0 ? "+" : "").Append(rec.GoalDifference);
            if (i == 0) sb.Append(" - Champion");
            sb.AppendLine();
        }
        return sb.ToString().TrimEnd();
    }

    public static string Stats(CompetitionStats s, string title)
    {
        var sb = new StringBuilder();
        sb.AppendLine(title);
        sb.Append("- Matches: ").Append(s.Matches).AppendLine();
        sb.Append("- Total goals: ").Append(s.TotalGoals).AppendLine();
        sb.Append("- Average goals per match: ").Append(s.GoalsPerMatch.ToString("0.00", Inv)).AppendLine();
        sb.Append("- Home win rate: ").Append((s.HomeWinRate * 100).ToString("0.0", Inv)).Append("%").AppendLine();
        sb.Append("- Away win rate: ").Append((s.AwayWinRate * 100).ToString("0.0", Inv)).Append("%").AppendLine();
        sb.Append("- Draw rate: ").Append((s.DrawRate * 100).ToString("0.0", Inv)).Append("%");
        return sb.ToString();
    }

    public static string PlayerProfile(Player p)
    {
        var sb = new StringBuilder();
        sb.AppendLine(p.Name);
        sb.Append("- Nationality: ").Append(p.Nationality).AppendLine();
        sb.Append("- Age: ").Append(p.Age?.ToString(Inv) ?? "?").AppendLine();
        sb.Append("- Overall: ").Append(p.Overall?.ToString(Inv) ?? "?")
          .Append(", Potential: ").Append(p.Potential?.ToString(Inv) ?? "?").AppendLine();
        sb.Append("- Position: ").Append(p.Position ?? "?")
          .Append(", Jersey: ").Append(p.JerseyNumber ?? "?").AppendLine();
        sb.Append("- Club: ").Append(p.Club ?? "?").AppendLine();
        sb.Append("- Height: ").Append(p.Height ?? "?")
          .Append(", Weight: ").Append(p.Weight ?? "?");
        return sb.ToString();
    }
}
