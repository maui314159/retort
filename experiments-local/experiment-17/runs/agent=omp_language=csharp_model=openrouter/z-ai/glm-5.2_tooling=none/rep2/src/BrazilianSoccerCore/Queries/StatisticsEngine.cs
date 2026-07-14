using BrazilianSoccerCore.Models;

namespace BrazilianSoccerCore.Queries;

/// <summary>Aggregate statistical analysis over match collections.</summary>
public sealed class StatisticsEngine
{
    private readonly IReadOnlyList<Match> _matches;

    public StatisticsEngine(IReadOnlyList<Match> matches) => _matches = matches;

    /// <summary>Aggregate stats over a filtered set of matches.</summary>
    public MatchAggregateStats Aggregate(
        string? competition = null,
        int? season = null,
        DateTime? fromDate = null,
        DateTime? toDate = null)
    {
        var q = _matches.AsEnumerable();

        if (competition is not null)
            q = q.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season is not null)
            q = q.Where(m => m.Season == season);
        if (fromDate is not null)
            q = q.Where(m => m.Date >= fromDate);
        if (toDate is not null)
            q = q.Where(m => m.Date <= toDate);

        var scored = q.Where(m => m.HomeGoal is not null && m.AwayGoal is not null).ToList();
        var count = scored.Count;
        if (count == 0)
            return new MatchAggregateStats();

        var homeWins = scored.Count(m => m.HomeGoal > m.AwayGoal);
        var awayWins = scored.Count(m => m.AwayGoal > m.HomeGoal);
        var draws = scored.Count(m => m.HomeGoal == m.AwayGoal);
        var totalGoals = scored.Sum(m => m.HomeGoal!.Value + m.AwayGoal!.Value);

        return new MatchAggregateStats
        {
            Matches = count,
            HomeWins = homeWins,
            AwayWins = awayWins,
            Draws = draws,
            TotalGoals = totalGoals,
            AverageGoalsPerMatch = Math.Round((double)totalGoals / count, 2),
            HomeWinRate = Math.Round((double)homeWins / count * 100, 1),
            AwayWinRate = Math.Round((double)awayWins / count * 100, 1),
            DrawRate = Math.Round((double)draws / count * 100, 1),
        };
    }

    /// <summary>Average goals per match for a competition.</summary>
    public double AverageGoalsPerMatch(string? competition = null, int? season = null)
        => Aggregate(competition, season).AverageGoalsPerMatch;

    /// <summary>Season-by-season comparison of average goals and home-win rate.</summary>
    public List<(int Season, double AvgGoals, double HomeWinRate)> SeasonComparison(
        string competition, int fromSeason, int toSeason)
    {
        var result = new List<(int, double, double)>();
        for (var s = fromSeason; s <= toSeason; s++)
        {
            var agg = Aggregate(competition, s);
            if (agg.Matches > 0)
                result.Add((s, agg.AverageGoalsPerMatch, agg.HomeWinRate));
        }
        return result;
    }
}