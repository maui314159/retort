using System.Text;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Models;

namespace BrazilianSoccerMcp.Server.Services;

public sealed class StatisticsService
{
    private readonly SoccerDataContext _context;

    public StatisticsService(SoccerDataContext context)
    {
        _context = context;
    }

    public string GetAverageGoals(string? competition = null, int? season = null)
    {
        var query = _context.Matches.AsEnumerable();

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

        var matches = query.ToList();
        var totalGoals = matches.Sum(m => m.HomeGoals + m.AwayGoals);
        var avg = matches.Count > 0 ? (double)totalGoals / matches.Count : 0;

        var scope = string.IsNullOrWhiteSpace(competition) ? "all competitions" : competition;
        if (season.HasValue) scope += $" {season.Value}";

        return $"Average goals per match ({scope}): {avg:F2} over {matches.Count} matches";
    }

    public string GetBiggestWins(string? competition = null, int? limit = 10)
    {
        var query = _context.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) ||
                competition.Contains(m.Competition, StringComparison.OrdinalIgnoreCase));
        }

        var matches = query
            .Where(m => m.HomeGoals != m.AwayGoals)
            .Select(m => new { Match = m, Margin = Math.Abs(m.HomeGoals - m.AwayGoals) })
            .OrderByDescending(x => x.Margin)
            .ThenByDescending(x => x.Match.Date)
            .Take(limit ?? 10)
            .Select(x => x.Match)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine(string.IsNullOrWhiteSpace(competition)
            ? "Biggest wins in dataset:"
            : $"Biggest wins in {competition}:");

        for (int i = 0; i < matches.Count; i++)
        {
            var m = matches[i];
            var date = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown date";
            sb.AppendLine($"{i + 1}. {date}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition})");
        }

        return sb.ToString();
    }

    public string GetHomeWinRate(string? competition = null, int? season = null)
    {
        var query = _context.Matches.AsEnumerable();

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

        var matches = query.ToList();
        var homeWins = matches.Count(m => m.HomeGoals > m.AwayGoals);
        var rate = matches.Count > 0 ? (double)homeWins / matches.Count * 100 : 0;

        var scope = string.IsNullOrWhiteSpace(competition) ? "all competitions" : competition;
        if (season.HasValue) scope += $" {season.Value}";

        return $"Home win rate ({scope}): {rate:F1}% ({homeWins} home wins from {matches.Count} matches)";
    }
}
