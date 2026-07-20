// =============================================================================
// File: Query/StatisticsService.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Powers the "Statistical Analysis" capability:
//     - GetAverageGoals: average goals per match + home/away/draw rates
//     - GetBiggestWins: matches ranked by goal margin (biggest victories)
//     - GetTopScoringTeams: teams ranked by total goals for in a competition+season
//     - GetHomeAwayPerformance: home vs away win-rate split
//   Only completed matches (both goals known) contribute to the math.
// =============================================================================
namespace BrazilianSoccerMcp.Query;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

public sealed class StatisticsService
{
    private readonly SoccerDatabase _db;
    public StatisticsService(SoccerDatabase db) => _db = db;

    /// <summary>Aggregate goal / outcome rates for a competition (optionally season-scoped).</summary>
    public GoalsStatsDto GetAverageGoals(string? competition = null, int? season = null)
    {
        var dto = new GoalsStatsDto
        {
            Competition = string.IsNullOrWhiteSpace(competition) ? null : competition,
            Season = season,
        };
        int totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0, count = 0;
        foreach (var m in _db.Matches)
        {
            if (!string.IsNullOrWhiteSpace(competition)
                && !MatchQueryService.CompetitionMatches(m.Competition, competition))
                continue;
            if (season.HasValue && m.Season != season) continue;
            if (!m.HasResult) continue;

            count++;
            int hg = m.HomeGoal!.Value, ag = m.AwayGoal!.Value;
            totalGoals += hg + ag;
            if (hg > ag) homeWins++;
            else if (hg < ag) awayWins++;
            else draws++;
        }
        dto.Matches = count;
        dto.TotalGoals = totalGoals;
        dto.AverageGoalsPerMatch = count > 0 ? Math.Round((double)totalGoals / count, 2) : 0;
        dto.HomeWinRate = count > 0 ? Math.Round((double)homeWins / count * 100, 1) : 0;
        dto.AwayWinRate = count > 0 ? Math.Round((double)awayWins / count * 100, 1) : 0;
        dto.DrawRate = count > 0 ? Math.Round((double)draws / count * 100, 1) : 0;
        return dto;
    }

    /// <summary>Matches ranked by goal margin (winner first), largest margin first.</summary>
    public List<BiggestWinDto> GetBiggestWins(string? competition = null, int? season = null, int limit = 20)
    {
        var results = new List<BiggestWinDto>();
        foreach (var m in _db.Matches)
        {
            if (!string.IsNullOrWhiteSpace(competition)
                && !MatchQueryService.CompetitionMatches(m.Competition, competition))
                continue;
            if (season.HasValue && m.Season != season) continue;
            if (!m.HasResult) continue;
            int hg = m.HomeGoal!.Value, ag = m.AwayGoal!.Value;
            int margin = Math.Abs(hg - ag);
            if (margin == 0) continue;
            results.Add(new BiggestWinDto
            {
                Date = m.Date?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                Competition = m.Competition,
                HomeTeam = m.HomeTeam,
                AwayTeam = m.AwayTeam,
                HomeGoal = hg,
                AwayGoal = ag,
                Margin = margin,
                Season = m.Season,
            });
        }
        results.Sort((x, y) =>
        {
            var c = y.Margin.CompareTo(x.Margin);
            if (c != 0) return c;
            return string.Compare(y.Date ?? "", x.Date ?? "", StringComparison.Ordinal);
        });
        if (limit > 0 && results.Count > limit) results = results.GetRange(0, limit);
        return results;
    }

    /// <summary>Teams ranked by total goals scored (for) in a competition+season.</summary>
    public List<TeamScoringDto> GetTopScoringTeams(string competition, int season, int limit = 10)
    {
        var totals = new Dictionary<string, TeamScoringAccumulator>(StringComparer.Ordinal);
        foreach (var m in _db.Matches)
        {
            if (!MatchQueryService.CompetitionMatches(m.Competition, competition)) continue;
            if (m.Season != season) continue;
            if (!m.HasResult) continue;
            Accumulate(totals, m.HomeTeamNormalized, m.HomeTeam, m.HomeGoal!.Value, m.AwayGoal!.Value);
            Accumulate(totals, m.AwayTeamNormalized, m.AwayTeam, m.AwayGoal!.Value, m.HomeGoal!.Value);
        }
        var rows = new List<TeamScoringDto>();
        foreach (var kv in totals)
        {
            rows.Add(new TeamScoringDto
            {
                Team = string.IsNullOrEmpty(kv.Key) ? kv.Value.DisplayName : TeamNameNormalizer.CanonicalDisplay(kv.Key),
                Matches = kv.Value.Matches,
                GoalsFor = kv.Value.GoalsFor,
                GoalsAgainst = kv.Value.GoalsAgainst,
                AverageGoalsFor = kv.Value.Matches > 0
                    ? Math.Round((double)kv.Value.GoalsFor / kv.Value.Matches, 2)
                    : 0,
            });
        }
        rows.Sort((x, y) =>
        {
            var c = y.GoalsFor.CompareTo(x.GoalsFor);
            if (c != 0) return c;
            return y.AverageGoalsFor.CompareTo(x.AverageGoalsFor);
        });
        if (limit > 0 && rows.Count > limit) rows = rows.GetRange(0, limit);
        return rows;
    }

    /// <summary>Home vs away win/draw rates for a competition (optionally season-scoped).</summary>
    public GoalsStatsDto GetHomeAwayPerformance(string? competition = null, int? season = null)
        => GetAverageGoals(competition, season);

    private static void Accumulate(
        Dictionary<string, TeamScoringAccumulator> totals,
        string key, string displayName, int goalsFor, int goalsAgainst)
    {
        if (string.IsNullOrEmpty(key)) return;
        if (!totals.TryGetValue(key, out var a))
        {
            a = new TeamScoringAccumulator { DisplayName = displayName };
            totals[key] = a;
        }
        a.Matches++;
        a.GoalsFor += goalsFor;
        a.GoalsAgainst += goalsAgainst;
    }

    private sealed class TeamScoringAccumulator
    {
        public string DisplayName { get; set; } = "";
        public int Matches, GoalsFor, GoalsAgainst;
    }
}

public sealed class TeamScoringDto
{
    public string Team { get; set; } = "";
    public int Matches { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public double AverageGoalsFor { get; set; }
}
