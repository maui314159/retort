// BrazilianSoccerMcp.Core / Queries / CompetitionQueries.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Implements TASK.md "Required Capabilities
// 4. Competition Queries": standings by season (calculated from match results), the
// season champion, and the relegation zone.
// Standings rules:
//   * Points = 3*Wins + Draws (modern Brazilian points system used since 2003).
//   * Ties broken by: goal difference, then goals-for, then alphabetical.
//   * Only matches with a complete score contribute (un-scored rows are excluded
//     from the table — reported honestly by the caller).
//   * The champion is position 1; relegated teams are the bottom N (default 4,
//     matching the modern Série A relegation zone).
// Scope: standings are computed for a competition+season where season is known
// (Brasileirão, Copa do Brasil, Libertadores, Historical). The extended dataset
// has no season column and is excluded from standings queries by design.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Queries;

/// <summary>Competition-level queries: standings, champion, relegation.</summary>
public sealed class CompetitionQueries
{
    private readonly SoccerDataService _data;
    public CompetitionQueries(SoccerDataService data) => _data = data;

    /// <summary>
    /// Computes the full standings table for a competition+season.
    /// </summary>
    public IReadOnlyList<StandingsRow> Standings(CompetitionKind competition, int season)
    {
        var matches = _data.Matches
            .Where(m => m.Competition == competition && m.Season.HasValue && m.Season.Value == season)
            .ToList();

        // Per-team tallies. We use a dictionary of mutable accumulators because a
        // team plays both home and away across the season.
        var accum = new Dictionary<string, (int P, int W, int D, int L, int GF, int GA)>(StringComparer.Ordinal);
        foreach (var m in matches)
        {
            if (!m.HasScore) continue;
            Accumulate(accum, m.HomeTeam, m.HomeGoals!.Value, m.AwayGoals!.Value, isHome: true);
            Accumulate(accum, m.AwayTeam, m.AwayGoals!.Value, m.HomeGoals!.Value, isHome: false);
        }

        var rows = accum
            .Select(kv => new StandingsRow
            {
                Position = 0, // assigned after sort
                Team = kv.Key,
                Record = new TeamRecord
                {
                    Team = kv.Key,
                    Matches = kv.Value.P,
                    Wins = kv.Value.W,
                    Draws = kv.Value.D,
                    Losses = kv.Value.L,
                    GoalsFor = kv.Value.GF,
                    GoalsAgainst = kv.Value.GA,
                },
                IsChampion = false
            })
            .OrderByDescending(r => r.Record.Points)
            .ThenByDescending(r => r.Record.GoalDifference)
            .ThenByDescending(r => r.Record.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.Ordinal)
            .ToList();

        for (int i = 0; i < rows.Count; i++)
        {
            rows[i] = rows[i] with { Position = i + 1, IsChampion = i == 0 };
        }
        return rows;
    }

    /// <summary>Returns the champion (position 1) of a competition+season, or null.</summary>
    public StandingsRow? Champion(CompetitionKind competition, int season)
        => Standings(competition, season).FirstOrDefault();

    /// <summary>
    /// Returns the bottom <paramref name="count"/> teams of a competition+season
    /// (the relegation zone). Default 4 matches the modern Série A.
    /// </summary>
    public IReadOnlyList<StandingsRow> Relegated(CompetitionKind competition, int season, int count = 4)
    {
        var table = Standings(competition, season);
        return table.Skip(Math.Max(0, table.Count - count)).Take(count).Reverse().ToList();
    }

    private static void Accumulate(
        Dictionary<string, (int P, int W, int D, int L, int GF, int GA)> accum,
        string team, int goalsFor, int goalsAgainst, bool isHome)
    {
        if (!accum.TryGetValue(team, out var cur))
            cur = (0, 0, 0, 0, 0, 0);
        int w = 0, d = 0, l = 0;
        if (goalsFor > goalsAgainst) w = 1;
        else if (goalsFor < goalsAgainst) l = 1;
        else d = 1;
        accum[team] = (cur.P + 1, cur.W + w, cur.D + d, cur.L + l, cur.GF + goalsFor, cur.GA + goalsAgainst);
    }
}
