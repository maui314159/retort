// =============================================================================
// File: Query/CompetitionQueryService.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Powers the "Competition Queries" capability:
//     - GetStandings: compute a league table from match results for a given
//       competition + season. Win = 3 pts, draw = 1, loss = 0. Sorted by
//       points, then goal difference, then goals for.
//     - GetCompetitionInfo: rounds/match counts for a competition+season
//     - FindFinals: cup knockout finals (matches whose round/stage mentions
//       "final") — used for "Find all Copa do Brasil finals" queries.
//   Standings only include competitions that follow a league format
//   (Brasileirão, Serie B, Serie C). Knockout competitions (Copa do Brasil,
//   Libertadores) don't have a meaningful league table; GetStandings returns
//   an empty list with a note for those.
// =============================================================================
namespace BrazilianSoccerMcp.Query;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

public sealed class CompetitionQueryService
{
    private readonly SoccerDatabase _db;
    public CompetitionQueryService(SoccerDatabase db) => _db = db;

    /// <summary>
    /// Compute league standings for <paramref name="competition"/> +
    /// <paramref name="season"/>. Only league-format competitions are
    /// table-eligible (Brasileirão, Serie B, Serie C).
    /// </summary>
    public List<StandingRowDto> GetStandings(string competition, int season)
    {
        if (!IsLeagueCompetition(competition)) return new List<StandingRowDto>();

        var table = new Dictionary<string, StandingAccumulator>(StringComparer.Ordinal);
        foreach (var m in _db.Matches)
        {
            if (!MatchQueryService.CompetitionMatches(m.Competition, competition)) continue;
            if (m.Season != season) continue;
            if (!m.HasResult) continue;
            Ensure(table, m.HomeTeamNormalized, m.HomeTeam);
            Ensure(table, m.AwayTeamNormalized, m.AwayTeam);
            var home = table[m.HomeTeamNormalized];
            var away = table[m.AwayTeamNormalized];
            int hg = m.HomeGoal!.Value;
            int ag = m.AwayGoal!.Value;
            home.Matches++; away.Matches++;
            home.GoalsFor += hg; home.GoalsAgainst += ag;
            away.GoalsFor += ag; away.GoalsAgainst += hg;
            if (hg > ag) { home.Wins++; away.Losses++; home.Points += 3; }
            else if (hg < ag) { away.Wins++; home.Losses++; away.Points += 3; }
            else { home.Draws++; away.Draws++; home.Points++; away.Points++; }
        }

        var rows = new List<StandingRowDto>();
        foreach (var kv in table)
        {
            var a = kv.Value;
            rows.Add(new StandingRowDto
            {
                Team = string.IsNullOrEmpty(kv.Key) ? a.DisplayName : TeamNameNormalizer.CanonicalDisplay(kv.Key),
                Matches = a.Matches,
                Wins = a.Wins,
                Draws = a.Draws,
                Losses = a.Losses,
                GoalsFor = a.GoalsFor,
                GoalsAgainst = a.GoalsAgainst,
                GoalDifference = a.GoalsFor - a.GoalsAgainst,
                Points = a.Points,
            });
        }
        rows.Sort((x, y) =>
        {
            var c = y.Points.CompareTo(x.Points);
            if (c != 0) return c;
            c = y.GoalDifference.CompareTo(x.GoalDifference);
            if (c != 0) return c;
            return y.GoalsFor.CompareTo(x.GoalsFor);
        });
        for (int i = 0; i < rows.Count; i++) rows[i].Position = i + 1;
        return rows;
    }

    /// <summary>Competition + season summary: distinct rounds, total matches, date range.</summary>
    public CompetitionInfoDto GetCompetitionInfo(string competition, int? season = null)
    {
        var info = new CompetitionInfoDto
        {
            Competition = competition,
            Season = season,
        };
        var rounds = new HashSet<string>();
        DateTime? min = null, max = null;
        foreach (var m in _db.Matches)
        {
            if (!MatchQueryService.CompetitionMatches(m.Competition, competition)) continue;
            if (season.HasValue && m.Season != season) continue;
            info.MatchCount++;
            if (!string.IsNullOrWhiteSpace(m.Round)) rounds.Add(m.Round!);
            else if (!string.IsNullOrWhiteSpace(m.Stage)) rounds.Add(m.Stage!);
            if (m.Date.HasValue)
            {
                if (min == null || m.Date < min) min = m.Date;
                if (max == null || m.Date > max) max = m.Date;
            }
        }
        info.Rounds = rounds.OrderBy(x => x, Comparer<string>.Create(NaturalRoundOrder)).ToList();
        info.FirstMatchDate = min?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        info.LastMatchDate = max?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        return info;
    }

    /// <summary>Find knockout finals (round/stage text mentions "final").</summary>
    public List<MatchResultDto> FindFinals(string? competition = null, int? season = null, int limit = 50)
    {
        var results = new List<MatchResultDto>();
        foreach (var m in _db.Matches)
        {
            bool isFinal = (m.Round != null && m.Round.Contains("final", StringComparison.OrdinalIgnoreCase))
                        || (m.Stage != null && m.Stage.Contains("final", StringComparison.OrdinalIgnoreCase));
            if (!isFinal) continue;
            if (!string.IsNullOrWhiteSpace(competition)
                && !MatchQueryService.CompetitionMatches(m.Competition, competition))
                continue;
            if (season.HasValue && m.Season != season) continue;
            results.Add(MatchQueryService.ToDto(m));
        }
        results.Sort(MatchQueryService.CompareByDateDesc);
        if (limit > 0 && results.Count > limit) results = results.GetRange(0, limit);
        return results;
    }

    // ---------------------------------------------------------------------
    private static bool IsLeagueCompetition(string competition)
    {
        if (string.IsNullOrWhiteSpace(competition)) return false;
        var c = competition.Trim().ToLowerInvariant();
        return c == "brasileirão" || c == "brasileirao"
            || c == "serie a" || c == "série a"
            || c == "serie b" || c == "série b"
            || c == "serie c" || c == "série c";
    }

    private static void Ensure(Dictionary<string, StandingAccumulator> table, string key, string displayName)
    {
        if (string.IsNullOrEmpty(key)) return;
        if (!table.ContainsKey(key))
            table[key] = new StandingAccumulator { DisplayName = displayName };
    }

    /// <summary>Natural ordering: numeric rounds first, then lexically.</summary>
    private static int NaturalRoundOrder(string a, string b)
    {
        bool aNum = int.TryParse(a, out var ai);
        bool bNum = int.TryParse(b, out var bi);
        if (aNum && bNum) return ai.CompareTo(bi);
        if (aNum) return -1;
        if (bNum) return 1;
        return string.Compare(a, b, StringComparison.OrdinalIgnoreCase);
    }

    private sealed class StandingAccumulator
    {
        public string DisplayName { get; set; } = "";
        public int Matches, Wins, Draws, Losses, GoalsFor, GoalsAgainst, Points;
    }
}

public sealed class CompetitionInfoDto
{
    public string Competition { get; set; } = "";
    public int? Season { get; set; }
    public int MatchCount { get; set; }
    public List<string> Rounds { get; set; } = new();
    public string? FirstMatchDate { get; set; }
    public string? LastMatchDate { get; set; }
}
