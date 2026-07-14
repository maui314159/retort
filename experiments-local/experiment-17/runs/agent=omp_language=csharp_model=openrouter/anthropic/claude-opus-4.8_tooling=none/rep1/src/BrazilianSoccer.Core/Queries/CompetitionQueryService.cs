// -----------------------------------------------------------------------------
// File: Queries/CompetitionQueryService.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Implements the "Competition Queries" capability from TASK.md: league tables
//   calculated from match results, the champion of a season, and relegation
//   (bottom-N) for a season. Backs "Who won the 2019 Brasileirão?" and "Which
//   teams were relegated in 2020?".
//
//   Standings are computed from the CANONICAL match set so overlapping source
//   files never inflate points. Only decided matches count. Teams are keyed by
//   their accent/case/suffix-folded MatchKey so the same club is one table row
//   regardless of which naming convention a given row used; the display name is
//   the most frequently seen canonical spelling for that key.
//
//   Ranking follows Brazilian league convention: points, then wins, then goal
//   difference, then goals for, then name (deterministic tie-break). This is a
//   reasonable reconstruction; true official tables also use head-to-head and
//   disciplinary records that the datasets do not contain, so callers are told
//   the table is "calculated from matches".
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Calculated league tables and season outcomes.</summary>
public sealed class CompetitionQueryService
{
    private readonly SoccerDataStore _store;

    public CompetitionQueryService(SoccerDataStore store) => _store = store;

    /// <summary>
    /// Builds the full calculated table for a competition + season, ordered best
    /// to worst. Returns an empty table when no decided matches exist for the pair.
    /// </summary>
    public Standings Table(Competition competition, int season)
    {
        // Accumulate per-team tallies keyed by folded name.
        var acc = new Dictionary<string, MutableRecord>();

        foreach (var m in _store.CanonicalMatches)
        {
            if (m.Competition != competition || m.Season != season || !m.HasResult)
                continue;

            var home = GetOrAdd(acc, m.HomeTeam);
            var away = GetOrAdd(acc, m.AwayTeam);

            int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
            home.Note(m.HomeTeam);
            away.Note(m.AwayTeam);

            home.Played++; away.Played++;
            home.GoalsFor += hg; home.GoalsAgainst += ag;
            away.GoalsFor += ag; away.GoalsAgainst += hg;

            if (hg > ag) { home.Wins++; away.Losses++; }
            else if (ag > hg) { away.Wins++; home.Losses++; }
            else { home.Draws++; away.Draws++; }
        }

        var ordered = acc.Values
            .Select(r => r.ToRecord())
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.Wins)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.OrdinalIgnoreCase)
            .ToList();

        var rows = new List<StandingRow>(ordered.Count);
        for (int i = 0; i < ordered.Count; i++)
            rows.Add(new StandingRow { Position = i + 1, Record = ordered[i] });

        return new Standings { Competition = competition, Season = season, Rows = rows };
    }

    /// <summary>The champion (table-topper) of a competition + season, or null if no data.</summary>
    public TeamRecord? Champion(Competition competition, int season)
        => Table(competition, season).Rows.FirstOrDefault()?.Record;

    /// <summary>
    /// The bottom <paramref name="count"/> teams of a season's table (the typical
    /// relegation set in Série A is 4). Fewer rows are returned when the table is
    /// smaller than <paramref name="count"/>.
    /// </summary>
    public IReadOnlyList<StandingRow> Relegated(Competition competition, int season, int count = 4)
    {
        var rows = Table(competition, season).Rows;
        if (rows.Count <= count)
            return rows;
        return rows.Skip(rows.Count - count).ToList();
    }

    /// <summary>Seasons for which a competition has at least one decided match.</summary>
    public IReadOnlyList<int> SeasonsFor(Competition competition)
        => _store.CanonicalMatches
            .Where(m => m.Competition == competition && m.Season is not null && m.HasResult)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();

    private static MutableRecord GetOrAdd(Dictionary<string, MutableRecord> acc, string team)
    {
        var key = TeamName.MatchKey(team);
        if (!acc.TryGetValue(key, out var r))
            acc[key] = r = new MutableRecord();
        return r;
    }

    // Mutable accumulator; also tracks the most common display spelling per team.
    private sealed class MutableRecord
    {
        private readonly Dictionary<string, int> _names = new(StringComparer.Ordinal);

        public int Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst;

        public void Note(string displayName)
            => _names[displayName] = _names.GetValueOrDefault(displayName) + 1;

        private string BestName()
            => _names.OrderByDescending(kv => kv.Value)
                     .ThenBy(kv => kv.Key, StringComparer.Ordinal)
                     .First().Key;

        public TeamRecord ToRecord() => new()
        {
            Team = BestName(),
            Played = Played,
            Wins = Wins,
            Draws = Draws,
            Losses = Losses,
            GoalsFor = GoalsFor,
            GoalsAgainst = GoalsAgainst,
        };
    }
}
