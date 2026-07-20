// =============================================================================
// File: Query/MatchQueryService.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Powers the "Match Queries" capability from the spec:
//     - search matches by team (home/away/either), opponent, competition,
//       season, and/or date range
//     - find all matches between two specific teams (derby lookups)
//   The service resolves team names through TeamNameNormalizer so callers can
//   pass "Palmeiras-SP", "Palmeiras", or "Sociedade Esportiva Palmeiras" and
//   get the same hits. Results are capped by a configurable limit (default 50)
//   to keep MCP responses bounded, and ordered by date descending so the most
//   recent fixtures surface first.
// =============================================================================
namespace BrazilianSoccerMcp.Query;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

public sealed class MatchQueryService
{
    private readonly SoccerDatabase _db;
    public MatchQueryService(SoccerDatabase db) => _db = db;

    /// <summary>
    /// Search matches by team / opponent / competition / season / date range.
    /// Any filter may be null/empty (meaning "do not filter on this axis").
    /// <paramref name="team"/> matches either home or away side.
    /// </summary>
    public List<MatchResultDto> SearchMatches(
        string? team = null,
        string? opponent = null,
        string? competition = null,
        int? season = null,
        DateTime? startDate = null,
        DateTime? endDate = null,
        int limit = 50)
    {
        var teamKey = TeamNameNormalizer.Normalize(team);
        var oppKey = TeamNameNormalizer.Normalize(opponent);

        IEnumerable<MatchRecord> source = string.IsNullOrEmpty(teamKey)
            ? _db.Matches
            : _db.MatchesForTeam(teamKey);

        var results = new List<MatchResultDto>();
        foreach (var m in source)
        {
            if (!string.IsNullOrEmpty(oppKey))
            {
                bool homeVsOpp = string.Equals(m.HomeTeamNormalized, oppKey, StringComparison.Ordinal);
                bool awayVsOpp = string.Equals(m.AwayTeamNormalized, oppKey, StringComparison.Ordinal);
                if (!homeVsOpp && !awayVsOpp) continue;
                // When both team+opponent given, ensure the "team" actually plays too
                if (!string.IsNullOrEmpty(teamKey))
                {
                    bool teamIsHome = string.Equals(m.HomeTeamNormalized, teamKey, StringComparison.Ordinal);
                    bool teamIsAway = string.Equals(m.AwayTeamNormalized, teamKey, StringComparison.Ordinal);
                    if (!teamIsHome && !teamIsAway) continue;
                }
            }

            if (!string.IsNullOrWhiteSpace(competition)
                && !CompetitionMatches(m.Competition, competition))
                continue;

            if (season.HasValue && m.Season != season) continue;

            if (startDate.HasValue && (!m.Date.HasValue || m.Date < startDate)) continue;
            if (endDate.HasValue && (!m.Date.HasValue || m.Date > endDate)) continue;

            results.Add(ToDto(m));
            if (results.Count >= limit) break;
        }

        results.Sort(CompareByDateDesc);
        return results;
    }

    /// <summary>All matches between teamA and teamB (either order), newest first.</summary>
    public List<MatchResultDto> FindMatchesBetweenTeams(
        string teamA, string teamB, string? competition = null, int? season = null, int limit = 100)
    {
        var a = TeamNameNormalizer.Normalize(teamA);
        var b = TeamNameNormalizer.Normalize(teamB);
        if (a.Length == 0 || b.Length == 0) return new List<MatchResultDto>();

        var results = new List<MatchResultDto>();
        // Iterate the smaller of the two team indexes.
        var listA = _db.MatchesForTeam(a);
        foreach (var m in listA)
        {
            bool involvesB = string.Equals(m.HomeTeamNormalized, b, StringComparison.Ordinal)
                          || string.Equals(m.AwayTeamNormalized, b, StringComparison.Ordinal);
            if (!involvesB) continue;
            if (!string.IsNullOrWhiteSpace(competition)
                && !CompetitionMatches(m.Competition, competition))
                continue;
            if (season.HasValue && m.Season != season) continue;
            results.Add(ToDto(m));
        }
        results.Sort(CompareByDateDesc);
        if (limit > 0 && results.Count > limit) results = results.GetRange(0, limit);
        return results;
    }

    public static bool CompetitionMatches(string recordCompetition, string requested)
    {
        if (string.IsNullOrWhiteSpace(requested)) return true;
        var r = requested.Trim();
        // Tolerate common aliases a caller (LLM) might pass.
        return r.ToLowerInvariant() switch
        {
            "brasileirao" or "brasileirão" or "serie a" or "série a"
                => string.Equals(recordCompetition, MatchLoader.Brasileirao, StringComparison.Ordinal),
            "copa do brasil" or "brazilian cup" or "copa"
                => string.Equals(recordCompetition, MatchLoader.CopaDoBrasil, StringComparison.Ordinal),
            "libertadores" or "copa libertadores"
                => string.Equals(recordCompetition, MatchLoader.Libertadores, StringComparison.Ordinal),
            _ => string.Equals(recordCompetition, r, StringComparison.OrdinalIgnoreCase),
        };
    }

    internal static int CompareByDateDesc(MatchResultDto x, MatchResultDto y)
    {
        // Null/unknown dates sort last.
        if (string.IsNullOrEmpty(x.Date) && string.IsNullOrEmpty(y.Date)) return 0;
        if (string.IsNullOrEmpty(x.Date)) return 1;
        if (string.IsNullOrEmpty(y.Date)) return -1;
        return string.Compare(y.Date, x.Date, StringComparison.Ordinal);
    }

    internal static MatchResultDto ToDto(MatchRecord m)
    {
        string? winner = null;
        if (m.HasResult)
        {
            var hg = m.HomeGoal!.Value;
            var ag = m.AwayGoal!.Value;
            winner = hg == ag ? "draw" : (hg > ag ? "home" : "away");
        }
        return new MatchResultDto
        {
            Competition = m.Competition,
            HomeTeam = m.HomeTeam,
            AwayTeam = m.AwayTeam,
            HomeGoal = m.HomeGoal,
            AwayGoal = m.AwayGoal,
            Date = m.Date?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
            Season = m.Season,
            Round = m.Round,
            Stage = m.Stage,
            Arena = m.Arena,
            SourceFile = m.SourceFile,
            Winner = winner,
        };
    }
}
