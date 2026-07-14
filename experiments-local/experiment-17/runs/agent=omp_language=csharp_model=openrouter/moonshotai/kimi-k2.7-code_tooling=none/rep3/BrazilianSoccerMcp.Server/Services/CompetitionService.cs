using System.Text;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Models;

namespace BrazilianSoccerMcp.Server.Services;

public sealed class CompetitionService
{
    private readonly SoccerDataContext _context;

    public CompetitionService(SoccerDataContext context)
    {
        _context = context;
    }

    public IReadOnlyList<TeamStanding> GetStandings(string competition, int season)
    {
        var matches = _context.Matches
            .Where(m => m.Season == season)
            .Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) ||
                competition.Contains(m.Competition, StringComparison.OrdinalIgnoreCase))
            .ToList();

        var standings = new Dictionary<string, TeamStanding>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            var home = GetCanonicalTeam(m.HomeTeam);
            var away = GetCanonicalTeam(m.AwayTeam);

            RecordMatch(standings, home, m.HomeGoals, m.AwayGoals);
            RecordMatch(standings, away, m.AwayGoals, m.HomeGoals);
        }

        return standings.Values
            .OrderByDescending(s => s.Points)
            .ThenByDescending(s => s.GoalDifference)
            .ThenByDescending(s => s.GoalsFor)
            .ToList();
    }

    public string FormatStandings(string competition, int season, IReadOnlyList<TeamStanding> standings)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"{season} {competition} Final Standings (calculated from matches):");

        if (standings.Count == 0)
        {
            sb.AppendLine("No matches found for this competition/season.");
            return sb.ToString();
        }

        for (int i = 0; i < standings.Count; i++)
        {
            var s = standings[i];
            var suffix = i == 0 ? " - Champion" : string.Empty;
            sb.AppendLine($"{i + 1}. {s.Team} - {s.Points} pts ({s.Wins}W, {s.Draws}D, {s.Losses}L){suffix}");
        }

        return sb.ToString();
    }

    public IReadOnlyList<MatchRecord> GetBracket(string competition, int season, string stage)
    {
        return _context.Matches
            .Where(m => m.Season == season)
            .Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) ||
                competition.Contains(m.Competition, StringComparison.OrdinalIgnoreCase))
            .Where(m =>
                (m.Stage?.Contains(stage, StringComparison.OrdinalIgnoreCase) ?? false) ||
                (m.Round?.Contains(stage, StringComparison.OrdinalIgnoreCase) ?? false))
            .OrderBy(m => m.Date)
            .ToList();
    }

    private static string GetCanonicalTeam(string team)
    {
        // Return the original name as the canonical name; normalization is used for comparison
        return team.Trim();
    }

    private static void RecordMatch(Dictionary<string, TeamStanding> standings, string team, int gf, int ga)
    {
        if (!standings.TryGetValue(team, out var standing))
        {
            standing = new TeamStanding(team);
            standings[team] = standing;
        }

        standing.AddMatch(gf, ga);
    }
}

public sealed class TeamStanding
{
    public string Team { get; }
    public int Played { get; private set; }
    public int Wins { get; private set; }
    public int Draws { get; private set; }
    public int Losses { get; private set; }
    public int GoalsFor { get; private set; }
    public int GoalsAgainst { get; private set; }
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public int Points => Wins * 3 + Draws;

    public TeamStanding(string team)
    {
        Team = team;
    }

    public void AddMatch(int gf, int ga)
    {
        Played++;
        GoalsFor += gf;
        GoalsAgainst += ga;
        if (gf > ga) Wins++;
        else if (gf == ga) Draws++;
        else Losses++;
    }
}
