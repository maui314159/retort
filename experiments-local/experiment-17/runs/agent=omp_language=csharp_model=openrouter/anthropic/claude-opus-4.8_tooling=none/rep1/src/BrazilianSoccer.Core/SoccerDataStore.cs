// -----------------------------------------------------------------------------
// File: SoccerDataStore.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   The in-memory knowledge graph. Loads every match and player CSV once and
//   exposes two immutable match views plus the player list. Query services read
//   from this store; it is never mutated after construction, so it is safe to
//   share across concurrent MCP tool invocations.
//
//   The central problem this type solves is OVERLAP. The same Série A season can
//   appear in up to three files (Brasileirao_Matches 2012-2022, the historical
//   file 2003-2019, and the extended-stats file by date). Naively concatenating
//   them would double- or triple-count fixtures and wreck standings and averages.
//
//   So we build a DEDUPLICATED canonical set: group every match by
//   (competition, season) and keep only the rows from the single highest-priority
//   source that actually covers that bucket. Priorities are fixed per competition
//   (see SourcePriority) so the choice is deterministic and testable:
//     - Série A : Brasileirao_Matches > Historical > ExtendedStats
//     - Série B/C: ExtendedStats (only source)
//     - Copa do Brasil: BrazilianCup > ExtendedStats
//     - Libertadores: LibertadoresMatches
//   Buckets that only one source covers (e.g. 2023 Série A, which lives solely in
//   ExtendedStats; or pre-2012 seasons only in the historical file) are preserved.
//
//   Matches lacking a season are kept verbatim in the canonical set (they cannot
//   collide on a (competition, season) key and dropping them would lose data).
//
//   AllMatches exposes the raw, un-deduplicated union for callers that explicitly
//   want every source row (e.g. richest-stats lookups). Standings/statistics/
//   match queries use CanonicalMatches.
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Data;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core;

/// <summary>Immutable in-memory store of all matches and players.</summary>
public sealed class SoccerDataStore
{
    private SoccerDataStore(
        IReadOnlyList<Match> allMatches,
        IReadOnlyList<Match> canonicalMatches,
        IReadOnlyList<Player> players)
    {
        AllMatches = allMatches;
        CanonicalMatches = canonicalMatches;
        Players = players;
    }

    /// <summary>Every match row from every file (overlaps NOT removed).</summary>
    public IReadOnlyList<Match> AllMatches { get; }

    /// <summary>One row per fixture: overlapping (competition, season) buckets deduplicated.</summary>
    public IReadOnlyList<Match> CanonicalMatches { get; }

    /// <summary>Every FIFA player.</summary>
    public IReadOnlyList<Player> Players { get; }

    /// <summary>Loads all datasets from the auto-resolved data directory.</summary>
    public static SoccerDataStore Load() => Load(DataPaths.Resolve());

    /// <summary>Loads all datasets from an explicit data directory.</summary>
    public static SoccerDataStore Load(string dataDir)
    {
        var matches = MatchLoader.LoadAll(dataDir);
        var players = PlayerLoader.LoadAll(dataDir);
        var canonical = Deduplicate(matches);
        return new SoccerDataStore(matches, canonical, players);
    }

    /// <summary>Constructs a store directly from in-memory data (used by tests).</summary>
    public static SoccerDataStore FromData(IEnumerable<Match> matches, IEnumerable<Player> players)
    {
        var all = matches.ToList();
        return new SoccerDataStore(all, Deduplicate(all), players.ToList());
    }

    // Fixed per-competition source ranking; lower index = higher priority.
    private static readonly Dictionary<Competition, DataSource[]> SourcePriority = new()
    {
        [Competition.BrasileiraoSerieA] =
            [DataSource.BrasileiraoMatches, DataSource.HistoricalBrasileirao, DataSource.ExtendedStats],
        [Competition.BrasileiraoSerieB] = [DataSource.ExtendedStats],
        [Competition.BrasileiraoSerieC] = [DataSource.ExtendedStats],
        [Competition.CopaDoBrasil] = [DataSource.BrazilianCupMatches, DataSource.ExtendedStats],
        [Competition.Libertadores] = [DataSource.LibertadoresMatches],
    };

    private static List<Match> Deduplicate(IReadOnlyList<Match> matches)
    {
        var result = new List<Match>(matches.Count);

        // Group only the rows that can collide: those with a known season.
        // Rows without a season are passed through untouched.
        var byBucket = new Dictionary<(Competition, int), List<Match>>();
        foreach (var m in matches)
        {
            if (m.Season is null)
            {
                result.Add(m);
                continue;
            }
            var key = (m.Competition, m.Season.Value);
            if (!byBucket.TryGetValue(key, out var list))
                byBucket[key] = list = new List<Match>();
            list.Add(m);
        }

        foreach (var ((competition, _), bucket) in byBucket)
        {
            var chosen = ChooseSource(competition, bucket);
            foreach (var m in bucket)
                if (m.Source == chosen)
                    result.Add(m);
        }

        return result;
    }

    // Picks the highest-priority source present in the bucket. Falls back to the
    // source with the most rows when the competition has no configured priority
    // or none of the ranked sources are present.
    private static DataSource ChooseSource(Competition competition, List<Match> bucket)
    {
        var present = new HashSet<DataSource>();
        foreach (var m in bucket)
            present.Add(m.Source);

        if (SourcePriority.TryGetValue(competition, out var ranked))
            foreach (var s in ranked)
                if (present.Contains(s))
                    return s;

        // Fallback: most-populated source (deterministic by count then enum value).
        return bucket
            .GroupBy(m => m.Source)
            .OrderByDescending(g => g.Count())
            .ThenBy(g => g.Key)
            .First().Key;
    }
}
