// =============================================================================
// File: Query/TeamQueryService.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Powers the "Team Queries" capability:
//     - GetTeamStatistics: W/D/L, GF/GA, win rate for a team filtered by
//       season / competition / venue (home, away, or both)
//     - CompareTeams: head-to-head W/D/L plus goals across all matches
//       between two teams
//     - GetTeamCompetitions: which competition buckets a team appears in
//     - GetTeamMatchHistory: most recent N matches for a team
//   All team matching goes through the normalized team index on SoccerDatabase.
// =============================================================================
namespace BrazilianSoccerMcp.Query;

using System;
using System.Collections.Generic;
using System.Linq;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

public sealed class TeamQueryService
{
    private readonly SoccerDatabase _db;
    private readonly MatchQueryService _matches;
    public TeamQueryService(SoccerDatabase db, MatchQueryService matches)
    {
        _db = db;
        _matches = matches;
    }

    /// <summary>
    /// Aggregated stats for <paramref name="team"/> scoped by season/competition/venue.
    /// venue: "home", "away", or "both"/null.
    /// </summary>
    public TeamStatsDto GetTeamStatistics(
        string team, int? season = null, string? competition = null, string? venue = null)
    {
        var key = TeamNameNormalizer.Normalize(team);
        var dto = new TeamStatsDto
        {
            Team = string.IsNullOrEmpty(key) ? team : TeamNameNormalizer.CanonicalDisplay(key),
            Competition = string.IsNullOrWhiteSpace(competition) ? null : competition,
            Season = season,
            Venue = string.IsNullOrWhiteSpace(venue) ? "both" : venue.ToLowerInvariant(),
        };

        if (string.IsNullOrEmpty(key)) return dto;

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, count = 0;
        foreach (var m in _db.MatchesForTeam(key))
        {
            bool isHome = string.Equals(m.HomeTeamNormalized, key, StringComparison.Ordinal);
            bool isAway = string.Equals(m.AwayTeamNormalized, key, StringComparison.Ordinal);

            if (!FilterVenue(isHome, isAway, dto.Venue)) continue;
            if (season.HasValue && m.Season != season) continue;
            if (!string.IsNullOrWhiteSpace(competition)
                && !MatchQueryService.CompetitionMatches(m.Competition, competition))
                continue;
            if (!m.HasResult) continue;

            count++;
            int teamGoals = isHome ? m.HomeGoal!.Value : m.AwayGoal!.Value;
            int oppGoals = isHome ? m.AwayGoal!.Value : m.HomeGoal!.Value;
            gf += teamGoals;
            ga += oppGoals;
            if (teamGoals > oppGoals) wins++;
            else if (teamGoals < oppGoals) losses++;
            else draws++;
        }

        dto.Matches = count;
        dto.Wins = wins;
        dto.Draws = draws;
        dto.Losses = losses;
        dto.GoalsFor = gf;
        dto.GoalsAgainst = ga;
        dto.WinRate = count > 0 ? Math.Round((double)wins / count * 100, 1) : 0;
        dto.GoalsForAverage = count > 0 ? Math.Round((double)gf / count, 2) : 0;
        return dto;
    }

    private static bool FilterVenue(bool isHome, bool isAway, string? venue)
    {
        if (string.IsNullOrEmpty(venue) || venue == "both") return true;
        if (venue == "home") return isHome;
        if (venue == "away") return isAway;
        return true;
    }

    /// <summary>Head-to-head comparison across all matches between two teams.</summary>
    public HeadToHeadDto CompareTeams(string teamA, string teamB, int? season = null, string? competition = null, int limit = 20)
    {
        var a = TeamNameNormalizer.Normalize(teamA);
        var b = TeamNameNormalizer.Normalize(teamB);
        var dto = new HeadToHeadDto
        {
            TeamA = string.IsNullOrEmpty(a) ? teamA : TeamNameNormalizer.CanonicalDisplay(a),
            TeamB = string.IsNullOrEmpty(b) ? teamB : TeamNameNormalizer.CanonicalDisplay(b),
        };
        if (a.Length == 0 || b.Length == 0) return dto;

        int aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
        var recent = new List<MatchResultDto>();

        foreach (var m in _db.MatchesForTeam(a))
        {
            bool involvesB = string.Equals(m.HomeTeamNormalized, b, StringComparison.Ordinal)
                          || string.Equals(m.AwayTeamNormalized, b, StringComparison.Ordinal);
            if (!involvesB) continue;
            if (!string.IsNullOrWhiteSpace(competition)
                && !MatchQueryService.CompetitionMatches(m.Competition, competition))
                continue;
            if (season.HasValue && m.Season != season) continue;
            if (!m.HasResult) continue;

            int aGoalsInMatch = string.Equals(m.HomeTeamNormalized, a, StringComparison.Ordinal)
                ? m.HomeGoal!.Value : m.AwayGoal!.Value;
            int bGoalsInMatch = string.Equals(m.HomeTeamNormalized, b, StringComparison.Ordinal)
                ? m.HomeGoal!.Value : m.AwayGoal!.Value;
            aGoals += aGoalsInMatch;
            bGoals += bGoalsInMatch;

            if (aGoalsInMatch > bGoalsInMatch) aWins++;
            else if (aGoalsInMatch < bGoalsInMatch) bWins++;
            else draws++;

            recent.Add(MatchQueryService.ToDto(m));
        }

        recent.Sort(MatchQueryService.CompareByDateDesc);
        if (limit > 0 && recent.Count > limit)
            recent = recent.GetRange(0, limit);

        dto.Matches = aWins + bWins + draws;
        dto.TeamAWins = aWins;
        dto.TeamBWins = bWins;
        dto.Draws = draws;
        dto.TeamAGoals = aGoals;
        dto.TeamBGoals = bGoals;
        dto.RecentMatches = recent;
        return dto;
    }

    /// <summary>Distinct competition buckets the team has played in, with per-competition match counts.</summary>
    public Dictionary<string, int> GetTeamCompetitions(string team)
    {
        var key = TeamNameNormalizer.Normalize(team);
        var result = new Dictionary<string, int>();
        if (string.IsNullOrEmpty(key)) return result;
        foreach (var m in _db.MatchesForTeam(key))
        {
            if (string.IsNullOrEmpty(m.Competition)) continue;
            result.TryGetValue(m.Competition, out var c);
            result[m.Competition] = c + 1;
        }
        return result;
    }

    /// <summary>Most recent N matches for a team, newest first.</summary>
    public List<MatchResultDto> GetTeamMatchHistory(string team, int limit = 10, string? competition = null, int? season = null)
    {
        var key = TeamNameNormalizer.Normalize(team);
        if (string.IsNullOrEmpty(key)) return new List<MatchResultDto>();
        var results = new List<MatchResultDto>();
        foreach (var m in _db.MatchesForTeam(key))
        {
            if (!string.IsNullOrWhiteSpace(competition)
                && !MatchQueryService.CompetitionMatches(m.Competition, competition))
                continue;
            if (season.HasValue && m.Season != season) continue;
            results.Add(MatchQueryService.ToDto(m));
        }
        results.Sort(MatchQueryService.CompareByDateDesc);
        if (limit > 0 && results.Count > limit)
            results = results.GetRange(0, limit);
        return results;
    }
}
