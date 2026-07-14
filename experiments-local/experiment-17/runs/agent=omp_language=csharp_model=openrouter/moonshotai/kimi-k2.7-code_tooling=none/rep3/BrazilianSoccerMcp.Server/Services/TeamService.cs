using System.Text;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Models;

namespace BrazilianSoccerMcp.Server.Services;

public sealed class TeamService
{
    private readonly SoccerDataContext _context;

    public TeamService(SoccerDataContext context)
    {
        _context = context;
    }

    public TeamStatistics GetStatistics(string team, string? competition = null, int? season = null, bool homeOnly = false)
    {
        var query = _context.Matches.Where(m => m.InvolvesTeam(team));

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

        if (homeOnly)
        {
            query = query.Where(m => TeamNameNormalizer.IsSameTeam(m.HomeTeam, team));
        }

        var matches = query.ToList();
        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.IsSameTeam(m.HomeTeam, team);
            int gf = isHome ? m.HomeGoals : m.AwayGoals;
            int ga = isHome ? m.AwayGoals : m.HomeGoals;
            goalsFor += gf;
            goalsAgainst += ga;

            if (gf > ga) wins++;
            else if (gf == ga) draws++;
            else losses++;
        }

        return new TeamStatistics(team, matches.Count, wins, draws, losses, goalsFor, goalsAgainst);
    }

    public string FormatStatistics(TeamStatistics stats, string? scope = null)
    {
        var label = scope ?? $"{stats.Team}";
        var winRate = stats.Matches > 0 ? (double)stats.Wins / stats.Matches * 100 : 0;

        var sb = new StringBuilder();
        sb.AppendLine($"{label}:");
        sb.AppendLine($"- Matches: {stats.Matches}");
        sb.AppendLine($"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {winRate:F1}%");
        return sb.ToString();
    }
}

public sealed record TeamStatistics(
    string Team,
    int Matches,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst);
