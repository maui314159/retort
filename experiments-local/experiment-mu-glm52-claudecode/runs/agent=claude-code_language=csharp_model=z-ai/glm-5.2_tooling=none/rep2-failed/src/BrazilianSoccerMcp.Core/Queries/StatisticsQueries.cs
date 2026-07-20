// BrazilianSoccerMcp.Core / Queries / StatisticsQueries.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Implements TASK.md "Required Capabilities
// 5. Statistical Analysis": goals-per-match averages, team performance trends,
// head-to-head records (delegated to MatchQueries), home vs away performance, and
// biggest wins in the dataset.
// Definitions:
//   * Average goals per match = sum(home+away) / number-of-scored-matches.
//   * Home win rate = matches where home team out-scored away / scored matches.
//   * Biggest wins are ranked by goal difference, then by winner's goals, across
//     the (optionally competition/season-filtered) match set.
//   * A "performance trend" is the team's per-season record in a competition.
// All calculations ignore un-scored rows (some Libertadores rows have no goals),
// and that exclusion is surfaced through the count fields rather than hidden.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Queries;

/// <summary>Aggregate statistical queries across the loaded match data.</summary>
public sealed class StatisticsQueries
{
    private readonly SoccerDataService _data;
    public StatisticsQueries(SoccerDataService data) => _data = data;

    /// <summary>
    /// Average goals per match in a scope. If <paramref name="competition"/> is
    /// null, averages across all competitions.
    /// </summary>
    public (double AverageGoals, int MatchCount, double HomeWinRate, double AwayWinRate, double DrawRate) GoalStats(
        CompetitionKind? competition = null, int? season = null)
    {
        var scored = _data.Matches
            .Where(m => !competition.HasValue || m.Competition == competition.Value)
            .Where(m => !season.HasValue || (m.Season.HasValue && m.Season.Value == season.Value))
            .Where(m => m.HasScore)
            .ToList();

        if (scored.Count == 0)
            return (0, 0, 0, 0, 0);

        int totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
        foreach (var m in scored)
        {
            int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
            totalGoals += hg + ag;
            if (hg > ag) homeWins++;
            else if (ag > hg) awayWins++;
            else draws++;
        }
        return (
            (double)totalGoals / scored.Count,
            scored.Count,
            (double)homeWins / scored.Count,
            (double)awayWins / scored.Count,
            (double)draws / scored.Count);
    }

    /// <summary>
    /// Returns the <paramref name="limit"/> biggest victories in the (optionally
    /// filtered) match set, ranked by goal difference then winner's goals.
    /// </summary>
    public IReadOnlyList<BiggestWin> BiggestWins(int limit = 10, CompetitionKind? competition = null, int? season = null)
    {
        return _data.Matches
            .Where(m => !competition.HasValue || m.Competition == competition.Value)
            .Where(m => !season.HasValue || (m.Season.HasValue && m.Season.Value == season.Value))
            .Where(m => m.HasScore)
            .Select(m =>
            {
                int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
                var homeWon = hg >= ag; // ties broken toward home; ties excluded below
                var winner = homeWon ? m.HomeTeam : m.AwayTeam;
                var loser = homeWon ? m.AwayTeam : m.HomeTeam;
                var wGoals = homeWon ? hg : ag;
                var lGoals = homeWon ? ag : hg;
                return new BiggestWin
                {
                    Date = m.Date,
                    Winner = winner,
                    Loser = loser,
                    WinnerGoals = wGoals,
                    LoserGoals = lGoals,
                    Competition = m.CompetitionLabel,
                    Season = m.Season,
                };
            })
            .Where(w => w.WinnerGoals > w.LoserGoals) // exclude draws
            .OrderByDescending(w => w.GoalDifference)
            .ThenByDescending(w => w.WinnerGoals)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Per-season record trend for a team in a competition. Useful for
    /// "Compare the 2018 and 2019 seasons".
    /// </summary>
    public IReadOnlyList<(int Season, TeamRecord Record)> PerformanceTrend(
        string team, CompetitionKind? competition = null)
    {
        var keys = _data.ResolveTeamKeys(team);
        if (keys.Count == 0) return Array.Empty<(int, TeamRecord)>();
        var set = new HashSet<string>(keys, StringComparer.Ordinal);
        var teamQueries = new TeamQueries(_data);
        var seasons = _data.Matches
            .Where(m => set.Contains(m.HomeTeam) || set.Contains(m.AwayTeam))
            .Where(m => !competition.HasValue || m.Competition == competition.Value)
            .Where(m => m.Season.HasValue)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();

        var trend = new List<(int, TeamRecord)>();
        foreach (var s in seasons)
            trend.Add((s, teamQueries.TeamRecord(team, competition, s)));
        return trend;
    }

    /// <summary>
    /// Returns the team with the best home record in a scope, measured by home win
    /// rate (min 5 matches). Implements "Which team has the best home record?".
    /// </summary>
    public (string Team, double HomeWinRate, int HomeMatches)? BestHomeRecord(
        CompetitionKind? competition = null, int? season = null, int minMatches = 5)
    {
        var scored = _data.Matches
            .Where(m => !competition.HasValue || m.Competition == competition.Value)
            .Where(m => !season.HasValue || (m.Season.HasValue && m.Season.Value == season.Value))
            .Where(m => m.HasScore)
            .ToList();

        var byHome = scored.GroupBy(m => m.HomeTeam, StringComparer.Ordinal)
            .Select(g =>
            {
                int w = g.Count(m => m.HomeGoals > m.AwayGoals);
                return (Team: g.Key, Wins: w, Total: g.Count());
            })
            .Where(x => x.Total >= minMatches)
            .Select(x => (x.Team, HomeWinRate: (double)x.Wins / x.Total, HomeMatches: x.Total))
            .OrderByDescending(x => x.HomeWinRate)
            .ThenByDescending(x => x.HomeMatches);

        return byHome.FirstOrDefault();
    }
}
