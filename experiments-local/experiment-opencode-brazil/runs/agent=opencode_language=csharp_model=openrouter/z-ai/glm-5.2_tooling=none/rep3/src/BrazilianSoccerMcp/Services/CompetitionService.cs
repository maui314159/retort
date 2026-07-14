using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Competition-level queries: standings (computed from match results), top
/// scoring teams, and biggest victories.
/// </summary>
public sealed class CompetitionService
{
    private readonly IReadOnlyList<MatchRecord> _matches;

    public CompetitionService(DataRepository repo)
    {
        _matches = repo.Matches;
    }

    /// <summary>Computes a standings table for the supplied competition and season.</summary>
    public StandingsTable GetStandings(string competition, int season)
    {
        var compKey = competition.Trim();
        var table = new Dictionary<string, StandingsRow>(StringComparer.OrdinalIgnoreCase);
        foreach (var m in _matches)
        {
            if (m.Season != season) continue;
            if (!m.Competition.Contains(compKey, StringComparison.OrdinalIgnoreCase)) continue;
            if (m.HomeGoal == 0 && m.AwayGoal == 0 && m.Date == DateTime.MinValue) continue;

            ProcessSide(table, m.HomeTeam, m.HomeGoal, m.AwayGoal, isHome: true);
            ProcessSide(table, m.AwayTeam, m.AwayGoal, m.HomeGoal, isHome: false);
        }

        var rows = table.Values.ToList();
        rows.Sort((a, b) =>
        {
            int c = b.Points.CompareTo(a.Points);
            if (c != 0) return c;
            c = b.GoalDifference.CompareTo(a.GoalDifference);
            if (c != 0) return c;
            return b.GoalsFor.CompareTo(a.GoalsFor);
        });
        for (int i = 0; i < rows.Count; i++) rows[i] = rows[i] with { Position = i + 1 };
        return new StandingsTable(competition, season, rows);
    }

    private static void ProcessSide(Dictionary<string, StandingsRow> table, string team, int gf, int ga, bool isHome)
    {
        if (string.IsNullOrEmpty(team)) return;
        if (!table.TryGetValue(team, out var row))
        {
            row = new StandingsRow(team, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        }
        row = row with
        {
            Played = row.Played + 1,
            GoalsFor = row.GoalsFor + gf,
            GoalsAgainst = row.GoalsAgainst + ga,
            GoalDifference = row.GoalDifference + gf - ga,
            HomeWins = row.HomeWins + (isHome && gf > ga ? 1 : 0),
            AwayWins = row.AwayWins + (!isHome && gf > ga ? 1 : 0),
        };
        if (gf > ga) row = row with { Wins = row.Wins + 1 };
        else if (gf == ga) row = row with { Draws = row.Draws + 1 };
        else row = row with { Losses = row.Losses + 1 };
        table[team] = row;
    }

    /// <summary>Biggest victories (largest goal margin) across the dataset.</summary>
    public IReadOnlyList<MatchRecord> BiggestVictories(string? competition = null, int? season = null, int limit = 10)
    {
        IEnumerable<MatchRecord> filtered = _matches;
        if (!string.IsNullOrEmpty(competition))
            filtered = filtered.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue) filtered = filtered.Where(m => m.Season == season.Value);

        return filtered
            .Where(m => m.Date != DateTime.MinValue && Math.Abs(m.HomeGoal - m.AwayGoal) > 0)
            .OrderByDescending(m => Math.Abs(m.HomeGoal - m.AwayGoal))
            .ThenByDescending(m => m.HomeGoal + m.AwayGoal)
            .Take(limit)
            .ToList();
    }

    /// <summary>Average goals per match and home-win rate across a competition.</summary>
    public MatchAverages GetAverages(string? competition = null, int? season = null)
    {
        IEnumerable<MatchRecord> filtered = _matches;
        if (!string.IsNullOrEmpty(competition))
            filtered = filtered.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue) filtered = filtered.Where(m => m.Season == season.Value);

        int total = 0, goals = 0, homeWins = 0, awayWins = 0, draws = 0;
        foreach (var m in filtered)
        {
            if (m.Date == DateTime.MinValue) continue;
            total++;
            goals += m.HomeGoal + m.AwayGoal;
            if (m.HomeGoal > m.AwayGoal) homeWins++;
            else if (m.HomeGoal < m.AwayGoal) awayWins++;
            else draws++;
        }
        return new MatchAverages(
            total,
            total > 0 ? (double)goals / total : 0,
            total > 0 ? (double)homeWins / total * 100 : 0,
            total > 0 ? (double)awayWins / total * 100 : 0,
            total > 0 ? (double)draws / total * 100 : 0);
    }

    /// <summary>Seasons available for a competition, descending.</summary>
    public IReadOnlyList<int> GetSeasons(string competition)
    {
        return _matches
            .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase))
            .Select(m => m.Season)
            .Distinct()
            .OrderByDescending(s => s)
            .ToList();
    }
}

public sealed record StandingsTable(string Competition, int Season, IReadOnlyList<StandingsRow> Rows);

public sealed record StandingsRow(
    string Team,
    int Position,
    int Played,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    int GoalDifference,
    int HomeWins,
    int AwayWins)
{
    public int Points => Wins * 3 + Draws;
}

public sealed record MatchAverages(
    int Matches,
    double AverageGoals,
    double HomeWinPercent,
    double AwayWinPercent,
    double DrawPercent);
