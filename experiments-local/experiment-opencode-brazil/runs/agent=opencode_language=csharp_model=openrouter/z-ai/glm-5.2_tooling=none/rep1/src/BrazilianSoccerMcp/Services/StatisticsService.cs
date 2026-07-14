// Context block
// File: Services/StatisticsService.cs
// Purpose: Aggregated statistical queries for the Brazilian Soccer MCP server. Computes
// average goals per match, home/away/draw win rates, biggest victories (sorted by goal
// margin), and per-team away records. All aggregations run over the in-memory match
// collection and respect competition/season filters. The service also provides a helper
// that returns the team with the best away record, which the spec calls out as a sample
// analytical question.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Aggregated statistics queries.</summary>
public sealed class StatisticsService
{
    private readonly SoccerDataStore _store;
    private readonly MatchService _matches;
    private readonly TeamService _teams;

    public StatisticsService(SoccerDataStore store, MatchService matches, TeamService teams)
    {
        _store = store;
        _matches = matches;
        _teams = teams;
    }

    /// <summary>Average goals per match across the filtered set.</summary>
    public double AverageGoalsPerMatch(Competition? competition = null, int? season = null)
    {
        var matches = _matches.SearchMatches(competition: competition, season: season);
        if (matches.Count == 0) return 0;
        var total = 0;
        foreach (var m in matches)
        {
            total += m.HomeGoal + m.AwayGoal;
        }
        return (double)total / matches.Count;
    }

    /// <summary>Home win / draw / away win rates across the filtered set.</summary>
    public OutcomeRates OutcomeRates(Competition? competition = null, int? season = null)
    {
        var matches = _matches.SearchMatches(competition: competition, season: season);
        if (matches.Count == 0)
        {
            return new OutcomeRates(0, 0, 0, 0);
        }
        int hw = 0, aw = 0, dr = 0;
        foreach (var m in matches)
        {
            if (m.HomeGoal > m.AwayGoal) hw++;
            else if (m.HomeGoal < m.AwayGoal) aw++;
            else dr++;
        }
        double total = matches.Count;
        return new OutcomeRates((double)hw / total * 100, (double)dr / total * 100,
            (double)aw / total * 100, matches.Count);
    }

    /// <summary>Returns the biggest victories by goal margin.</summary>
    public List<MatchRecord> BiggestWins(int topN = 10, Competition? competition = null, int? season = null)
    {
        var matches = _matches.SearchMatches(competition: competition, season: season);
        matches.Sort((a, b) =>
        {
            var ma = Math.Abs(a.HomeGoal - a.AwayGoal);
            var mb = Math.Abs(b.HomeGoal - b.AwayGoal);
            var byMargin = mb.CompareTo(ma);
            if (byMargin != 0) return byMargin;
            return a.Date.CompareTo(b.Date);
        });
        if (topN > 0 && matches.Count > topN)
        {
            matches = matches.GetRange(0, topN);
        }
        return matches;
    }

    /// <summary>Returns the team with the best away win rate (min matches).</summary>
    public TeamStats? BestAwayRecord(int? season = null, Competition? competition = null, int minMatches = 5)
    {
        var matches = _matches.SearchMatches(season: season, competition: competition);
        var teams = matches.SelectMany(m => new[] { _store.Normalizer.Normalize(m.Home), _store.Normalizer.Normalize(m.Away) })
            .Where(n => !string.IsNullOrWhiteSpace(n))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        TeamStats? best = null;
        foreach (var team in teams)
        {
            var stats = _teams.GetTeamStats(team, season, competition, Venue.Away);
            if (stats.Played < minMatches) continue;
            if (best is null || stats.WinRate > best.WinRate ||
                (stats.WinRate == best.WinRate && stats.Played > best.Played))
            {
                best = stats;
            }
        }
        return best;
    }
}

/// <summary>Win/draw/away-win percentage split.</summary>
public sealed record OutcomeRates(double HomeWinRate, double DrawRate, double AwayWinRate, int MatchCount);
