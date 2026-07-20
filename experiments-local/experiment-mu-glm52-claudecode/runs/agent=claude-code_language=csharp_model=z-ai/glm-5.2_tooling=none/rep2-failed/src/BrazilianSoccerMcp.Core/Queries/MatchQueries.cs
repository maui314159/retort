// BrazilianSoccerMcp.Core / Queries / MatchQueries.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Implements TASK.md "Required Capabilities
// 1. Match Queries": find matches by team, date range, competition, and season,
// plus head-to-head lookups.
// Team-matching model (see TeamNormalizer):
//   * A raw team name is resolved to the SET of canonical keys that refer to the
//     same club — suffix-tolerant, so "Flamengo" matches "flamengo-rj", but
//     distinct same-base clubs (Atlético-MG/-GO) never merge.
//   * A match is filtered in if its home or away canonical key is in that set.
//   * For head-to-head, teamA's key-set vs teamB's key-set: a fixture counts when
//     one side is in A's set and the other in B's set.
// All other filter parameters are optional (null = no restriction).
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;

namespace BrazilianSoccerMcp.Core.Queries;

/// <summary>
/// Optional filters applied to match queries. Every field is optional; null
/// means "no restriction on this axis". Record so callers can build derived
/// filters with `with` expressions.
/// </summary>
public sealed record MatchFilter
{
    public CompetitionKind? Competition { get; init; }
    public int? Season { get; init; }
    public DateTime? From { get; init; }
    public DateTime? Until { get; init; }

    public static MatchFilter Empty => new();
}

/// <summary>Match-related queries against the loaded soccer data.</summary>
public sealed class MatchQueries
{
    private readonly SoccerDataService _data;
    public MatchQueries(SoccerDataService data) => _data = data;

    /// <summary>
    /// Finds every match in which the team participated. Accepts raw, suffixed,
    /// or accented team forms ("Palmeiras-SP", "Palmeiras", "PALMEIRAS").
    /// </summary>
    public IReadOnlyList<Match> MatchesForTeam(string team, MatchFilter? filter = null)
    {
        var keys = _data.ResolveTeamKeys(team);
        if (keys.Count == 0) return Array.Empty<Match>();
        var set = new HashSet<string>(keys, StringComparer.Ordinal);
        return ApplyFilter(filter)
            .Where(m => set.Contains(m.HomeTeam) || set.Contains(m.AwayTeam))
            .OrderBy(m => m.Date ?? DateTime.MinValue)
            .ToList();
    }

    /// <summary>
    /// Finds matches between two specific teams (the Fla-Flu derby query).
    /// Returns matches chronologically regardless of which team is home/away.
    /// </summary>
    public IReadOnlyList<Match> MatchesBetween(string teamA, string teamB, MatchFilter? filter = null)
    {
        var keysA = new HashSet<string>(_data.ResolveTeamKeys(teamA), StringComparer.Ordinal);
        var keysB = new HashSet<string>(_data.ResolveTeamKeys(teamB), StringComparer.Ordinal);
        if (keysA.Count == 0 || keysB.Count == 0) return Array.Empty<Match>();
        return ApplyFilter(filter)
            .Where(m =>
                (keysA.Contains(m.HomeTeam) && keysB.Contains(m.AwayTeam)) ||
                (keysA.Contains(m.AwayTeam) && keysB.Contains(m.HomeTeam)))
            .OrderBy(m => m.Date ?? DateTime.MinValue)
            .ToList();
    }

    /// <summary>
    /// Returns matches in a date range across all competitions (or a competition-
    /// filtered subset).
    /// </summary>
    public IReadOnlyList<Match> MatchesInDateRange(DateTime from, DateTime until, MatchFilter? filter = null)
    {
        var f = new MatchFilter { From = from, Until = until, Competition = filter?.Competition, Season = filter?.Season };
        return ApplyFilter(f)
            .OrderBy(m => m.Date ?? DateTime.MinValue)
            .ToList();
    }

    /// <summary>
    /// Returns every match in a competition (optionally restricted to a season).
    /// </summary>
    public IReadOnlyList<Match> MatchesByCompetition(CompetitionKind competition, int? season = null)
        => ApplyFilter(new MatchFilter { Competition = competition, Season = season })
            .OrderBy(m => m.Date ?? DateTime.MinValue)
            .ToList();

    /// <summary>
    /// Head-to-head record between two teams across the (optionally filtered) match
    /// set. Counts wins/draws; un-scored matches are excluded from W/D/L.
    /// </summary>
    public HeadToHead HeadToHead(string teamA, string teamB, MatchFilter? filter = null)
    {
        var keysA = new HashSet<string>(_data.ResolveTeamKeys(teamA), StringComparer.Ordinal);
        var matches = MatchesBetween(teamA, teamB, filter);
        int aWins = 0, bWins = 0, draws = 0;
        foreach (var m in matches)
        {
            if (!m.HasScore) continue;
            int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
            if (hg == ag) { draws++; continue; }
            var aIsHome = keysA.Contains(m.HomeTeam);
            var homeWon = hg > ag;
            var aWon = aIsHome ? homeWon : !homeWon;
            if (aWon) aWins++; else bWins++;
        }
        // Display name: prefer the suffix-less normalized query; fall back to a key.
        var labelA = keysA.Count > 0 ? keysA.First() : teamA;
        var labelB = _data.ResolveTeamKeys(teamB).FirstOrDefault() ?? teamB;
        return new HeadToHead { TeamA = labelA, TeamB = labelB, TeamAWins = aWins, TeamBWins = bWins, Draws = draws };
    }

    // ----- shared filter -----------------------------------------------------

    private IEnumerable<Match> ApplyFilter(MatchFilter? filter)
    {
        var matches = _data.Matches;
        if (filter is null) return matches;

        IEnumerable<Match> seq = matches;
        if (filter.Competition.HasValue)
            seq = seq.Where(m => m.Competition == filter.Competition.Value);
        if (filter.Season.HasValue)
            seq = seq.Where(m => m.Season.HasValue && m.Season.Value == filter.Season.Value);
        if (filter.From.HasValue)
            seq = seq.Where(m => m.Date.HasValue && m.Date.Value >= filter.From.Value);
        if (filter.Until.HasValue)
            seq = seq.Where(m => m.Date.HasValue && m.Date.Value <= filter.Until.Value);
        return seq;
    }
}
