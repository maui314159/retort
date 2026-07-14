// -----------------------------------------------------------------------------
// File: Queries/StatisticsService.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Implements the "Statistical Analysis" capability from TASK.md: average goals
//   per match, home/away/draw rates, biggest victories, and best home/away
//   records across a competition+season scope. Backs "What's the average goals
//   per match in the Brasileirão?", "Which team has the best away record?",
//   "Show me the biggest wins in the dataset".
//
//   All aggregation runs over the CANONICAL match set (overlaps removed) so
//   averages and counts are not skewed by duplicate fixtures. Only decided
//   matches contribute. "Best record" intentionally requires a minimum number of
//   matches so a team with a single fluke win does not top the table.
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Aggregate statistical analysis over matches.</summary>
public sealed class StatisticsService
{
    private readonly SoccerDataStore _store;
    private readonly TeamQueryService _teams;

    public StatisticsService(SoccerDataStore store)
    {
        _store = store;
        _teams = new TeamQueryService(store);
    }

    /// <summary>
    /// Summary stats (avg goals, home/away/draw rates) over the matches matching
    /// the optional competition + season filters.
    /// </summary>
    public MatchStatsSummary Summary(Competition? competition = null, int? season = null)
    {
        int decided = 0, goals = 0, homeWins = 0, awayWins = 0, draws = 0;

        foreach (var m in Scope(competition, season))
        {
            if (!m.HasResult)
                continue;
            int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
            decided++;
            goals += hg + ag;
            if (hg > ag) homeWins++;
            else if (ag > hg) awayWins++;
            else draws++;
        }

        return new MatchStatsSummary
        {
            MatchesWithResult = decided,
            TotalGoals = goals,
            HomeWins = homeWins,
            AwayWins = awayWins,
            Draws = draws,
        };
    }

    /// <summary>
    /// The matches with the largest goal margin, descending, within the optional
    /// scope. Ties are broken by total goals then date (newest first).
    /// </summary>
    public IReadOnlyList<Match> BiggestVictories(
        Competition? competition = null, int? season = null, int limit = 10)
    {
        return Scope(competition, season)
            .Where(m => m.HasResult && m.HomeGoals != m.AwayGoals)
            .OrderByDescending(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value))
            .ThenByDescending(m => m.HomeGoals!.Value + m.AwayGoals!.Value)
            .ThenByDescending(m => m.Date ?? DateTime.MinValue)
            .Take(limit > 0 ? limit : 10)
            .ToList();
    }

    /// <summary>
    /// Teams ranked by record at the given venue (Home/Away/All), best first, among
    /// teams with at least <paramref name="minMatches"/> matches in scope. Ranking
    /// is by win rate, then points, then goal difference.
    /// </summary>
    public IReadOnlyList<TeamRecord> BestRecords(
        Venue venue = Venue.All,
        Competition? competition = null,
        int? season = null,
        int minMatches = 5,
        int limit = 10)
    {
        // Distinct team keys in scope, then compute each team's record once.
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var teams = new List<string>();
        foreach (var m in Scope(competition, season))
        {
            if (!m.HasResult) continue;
            if (seen.Add(TeamName.MatchKey(m.HomeTeam))) teams.Add(m.HomeTeam);
            if (seen.Add(TeamName.MatchKey(m.AwayTeam))) teams.Add(m.AwayTeam);
        }

        return teams
            .Select(t => _teams.RecordFor(t, competition, season, venue))
            .Where(r => r.Played >= minMatches)
            .OrderByDescending(r => r.WinRate)
            .ThenByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenBy(r => r.Team, StringComparer.OrdinalIgnoreCase)
            .Take(limit > 0 ? limit : 10)
            .ToList();
    }

    private IEnumerable<Match> Scope(Competition? competition, int? season)
    {
        IEnumerable<Match> q = _store.CanonicalMatches;
        if (competition is not null)
            q = q.Where(m => m.Competition == competition);
        if (season is not null)
            q = q.Where(m => m.Season == season);
        return q;
    }
}
