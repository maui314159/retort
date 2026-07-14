using System.Text;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Models;

namespace BrazilianSoccerMcp.Server.Services;

public sealed class MatchService
{
    private readonly SoccerDataContext _context;

    public MatchService(SoccerDataContext context)
    {
        _context = context;
    }

    public IReadOnlyList<MatchRecord> FindMatches(
        string? team = null,
        string? opponent = null,
        string? competition = null,
        int? season = null,
        DateTime? from = null,
        DateTime? to = null,
        string? stage = null,
        int? limit = null)
    {
        var query = _context.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team) && !string.IsNullOrWhiteSpace(opponent))
        {
            query = query.Where(m => m.IsBetween(team, opponent));
        }
        else if (!string.IsNullOrWhiteSpace(team))
        {
            query = query.Where(m => m.InvolvesTeam(team));
        }

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) ||
                competition.Contains(m.Competition, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        if (from.HasValue)
        {
            query = query.Where(m => m.Date >= from.Value);
        }

        if (to.HasValue)
        {
            query = query.Where(m => m.Date <= to.Value);
        }

        if (!string.IsNullOrWhiteSpace(stage))
        {
            query = query.Where(m =>
                (m.Stage?.Contains(stage, StringComparison.OrdinalIgnoreCase) ?? false) ||
                (m.Round?.Contains(stage, StringComparison.OrdinalIgnoreCase) ?? false));
        }

        query = query.OrderByDescending(m => m.Date);

        if (limit.HasValue)
        {
            query = query.Take(limit.Value);
        }

        return query.ToList();
    }

    public string FormatMatches(string teamA, string teamB, IEnumerable<MatchRecord> matches)
    {
        var list = matches.OrderByDescending(m => m.Date).ToList();
        var sb = new StringBuilder();
        sb.AppendLine($"{teamA} vs {teamB} matches:");

        if (list.Count == 0)
        {
            sb.AppendLine("No matches found.");
            return sb.ToString();
        }

        foreach (var m in list.Take(20))
        {
            var date = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown date";
            var comp = m.Competition;
            var detail = string.IsNullOrWhiteSpace(m.Round)
                ? (string.IsNullOrWhiteSpace(m.Stage) ? comp : $"{comp} {m.Stage}")
                : $"{comp} Round {m.Round}";
            sb.AppendLine($"- {date}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({detail})");
        }

        if (list.Count > 20)
        {
            sb.AppendLine($"... ({list.Count - 20} more matches in dataset)");
        }

        var winsA = list.Count(m =>
            (TeamNameNormalizer.IsSameTeam(m.HomeTeam, teamA) && m.HomeGoals > m.AwayGoals) ||
            (TeamNameNormalizer.IsSameTeam(m.AwayTeam, teamA) && m.AwayGoals > m.HomeGoals));
        var winsB = list.Count(m =>
            (TeamNameNormalizer.IsSameTeam(m.HomeTeam, teamB) && m.HomeGoals > m.AwayGoals) ||
            (TeamNameNormalizer.IsSameTeam(m.AwayTeam, teamB) && m.AwayGoals > m.HomeGoals));
        var draws = list.Count - winsA - winsB;

        sb.AppendLine();
        sb.AppendLine($"Head-to-head in dataset: {teamA} {winsA} wins, {teamB} {winsB} wins, {draws} draws");

        return sb.ToString();
    }
}
