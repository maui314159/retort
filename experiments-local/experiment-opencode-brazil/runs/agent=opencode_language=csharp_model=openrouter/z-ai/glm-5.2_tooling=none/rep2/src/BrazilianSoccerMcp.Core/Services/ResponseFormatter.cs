// BrazilianSoccerMcp.Core - Response formatting.
// Translates query results into the human-readable, spec-aligned response
// formats (e.g. "Flamengo vs Fluminense (Fla-Flu derby): ..."). These strings
// are what the MCP tools return to the LLM, which then surfaces them to the
// end user. Keeping formatting here keeps the tools thin.
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Services;

/// <summary>Formats query results into the response shapes described in the spec.</summary>
public static class ResponseFormatter
{
    public static string FormatHeadToHead(HeadToHead h)
    {
        if (h.Matches == 0)
            return $"No matches found between {h.TeamA} and {h.TeamB} in the dataset.";
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{h.TeamA} vs {h.TeamB}:");
        int shown = 0;
        foreach (var m in h.MatchesList.OrderByDescending(x => x.Date))
        {
            if (shown >= 20) { sb.AppendLine($"... ({h.Matches - shown} more matches in dataset)"); break; }
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.Score} {m.AwayTeam} ({CompetitionDisplay.Name(m.Competition)}{(FormatRound(m))})");
            shown++;
        }
        sb.AppendLine();
        sb.Append($"Head-to-head in dataset: {h.TeamA} {h.TeamAWins} wins, {h.TeamB} {h.TeamBWins} wins, {h.Draws} draws");
        return sb.ToString();
    }

    public static string FormatTeamStats(TeamStats s, string context)
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{s.Team} {context}:");
        sb.AppendLine($"- Matches: {s.Matches}");
        sb.AppendLine($"- Wins: {s.Wins}, Draws: {s.Draws}, Losses: {s.Losses}");
        sb.AppendLine($"- Goals For: {s.GoalsFor}, Goals Against: {s.GoalsAgainst}");
        if (s.HomeMatches > 0)
            sb.AppendLine($"- Home: {s.HomeMatches} matches, {s.HomeWins}W/{s.HomeDraws}D/{s.HomeLosses}L (win rate {s.HomeWinRate:P1})");
        if (s.AwayMatches > 0)
            sb.AppendLine($"- Away: {s.AwayMatches} matches, {s.AwayWins}W/{s.AwayDraws}D/{s.AwayLosses}L (win rate {s.AwayWinRate:P1})");
        if (s.Matches > 0)
            sb.AppendLine($"- Win rate: {s.WinRate:P1}");
        return sb.ToString();
    }

    public static string FormatStandings(IReadOnlyList<StandingsRow> rows, int season, Competition competition)
    {
        if (rows.Count == 0)
            return $"No standings data for {CompetitionDisplay.Name(competition)} {season}.";
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{season} {CompetitionDisplay.Name(competition)} Final Standings (calculated from matches):");
        foreach (var r in rows)
        {
            var tag = r.Champion ? " - Champion" : "";
            sb.AppendLine($"{r.Position}. {r.Team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L){tag}");
        }
        return sb.ToString();
    }

    public static string FormatBiggestWins(IReadOnlyList<Match> wins, double avgGoals,
        (double hw, double dr, double aw) winRates)
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Biggest victories in dataset:");
        int i = 1;
        foreach (var m in wins)
        {
            var winner = m.HomeGoal > m.AwayGoal ? m.HomeTeam : m.AwayTeam;
            var loser = m.HomeGoal > m.AwayGoal ? m.AwayTeam : m.HomeTeam;
            sb.AppendLine($"{i}. {m.Date:yyyy-MM-dd}: {winner} {m.Score} {loser} ({CompetitionDisplay.Name(m.Competition)})");
            i++;
        }
        sb.AppendLine();
        sb.AppendLine($"Average goals per match: {avgGoals:F2}");
        sb.AppendLine($"Home win rate: {winRates.hw:P1}, Draw rate: {winRates.dr:P1}, Away win rate: {winRates.aw:P1}");
        return sb.ToString();
    }

    public static string FormatPlayers(IReadOnlyList<Player> players, string title)
    {
        if (players.Count == 0) return $"{title}: no players found.";
        var sb = new System.Text.StringBuilder();
        sb.AppendLine(title);
        int i = 1;
        foreach (var p in players)
            sb.AppendLine($"{i}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}");
        return sb.ToString().TrimEnd();
    }

    public static string FormatBrazilianClubs(
        IReadOnlyList<(string Club, int Count, double AvgRating)> clubs)
    {
        if (clubs.Count == 0) return "No Brazilian players at Brazilian clubs found.";
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Brazilian players at Brazilian clubs:");
        foreach (var c in clubs)
            sb.AppendLine($"- {c.Club}: {c.Count} players (avg rating: {c.AvgRating:F0})");
        return sb.ToString().TrimEnd();
    }

    public static string FormatMatchList(IReadOnlyList<Match> matches, string title)
    {
        if (matches.Count == 0) return $"{title}: no matches found.";
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{title} ({matches.Count} matches):");
        int shown = 0;
        foreach (var m in matches.OrderByDescending(m => m.Date))
        {
            if (shown >= 30) { sb.AppendLine($"... ({matches.Count - shown} more)"); break; }
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.Score} {m.AwayTeam} ({CompetitionDisplay.Name(m.Competition)}{FormatRound(m)})");
            shown++;
        }
        return sb.ToString().TrimEnd();
    }

    private static string FormatRound(Match m)
    {
        if (!string.IsNullOrEmpty(m.Round)) return $" Round {m.Round}";
        if (!string.IsNullOrEmpty(m.Stage)) return $" {m.Stage}";
        return "";
    }
}
