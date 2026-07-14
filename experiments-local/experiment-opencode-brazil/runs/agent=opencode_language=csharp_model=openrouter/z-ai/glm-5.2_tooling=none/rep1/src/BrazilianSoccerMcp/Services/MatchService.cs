// Context block
// File: Services/MatchService.cs
// Purpose: Query API for the bundled match datasets of the Brazilian Soccer MCP server.
// Supports finding matches by team, opponent, competition, season, and date range, plus
// head-to-head summaries and "last match between two teams" lookups. All team-name
// comparisons go through the shared TeamNameNormalizer so spelling variants ("Palmeiras-SP"
// vs "Palmeiras" vs "Sociedade Esportiva Palmeiras") collapse to one canonical team.
// Results are sorted by date descending. The service is stateless and operates over the
// SoccerDataStore in-memory collection.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Match-level queries.</summary>
public sealed class MatchService
{
    private readonly SoccerDataStore _store;
    public TeamNameNormalizer Normalizer => _store.Normalizer;

    public MatchService(SoccerDataStore store) => _store = store;

    /// <summary>Finds matches for a team, optionally filtered by opponent, competition, season, and date range.</summary>
    public List<MatchRecord> SearchMatches(
        string? team = null,
        string? opponent = null,
        Competition? competition = null,
        int? season = null,
        DateTime? fromDate = null,
        DateTime? toDate = null)
    {
        var matches = _store.Matches;
        var result = new List<MatchRecord>();
        foreach (var m in matches)
        {
            if (competition is not null && m.CompetitionType != competition)
            {
                continue;
            }
            if (season is not null && m.Season != season)
            {
                continue;
            }
            if (fromDate is not null && m.Date < fromDate)
            {
                continue;
            }
            if (toDate is not null && m.Date > toDate)
            {
                continue;
            }
            if (team is not null && !TeamInvolved(m, team))
            {
                continue;
            }
            if (opponent is not null && !TeamInvolved(m, opponent))
            {
                continue;
            }
            if (team is not null && opponent is not null && !AreDistinct(team, opponent))
            {
                // Same team: keep.
            }
            else if (team is not null && opponent is not null)
            {
                // Both must be involved and the team must be on the opposite side of the opponent.
                if (!(TeamInvolved(m, team) && TeamInvolved(m, opponent)))
                {
                    continue;
                }
            }
            result.Add(m);
        }
        result.Sort((a, b) => b.Date.CompareTo(a.Date));
        return result;
    }

    /// <summary>Returns head-to-head matches and tallies for two teams.</summary>
    public HeadToHeadResult HeadToHead(string teamA, string teamB)
    {
        var matches = SearchMatches(team: teamA, opponent: teamB);
        var aNorm = Normalizer.Normalize(teamA);
        int aWins = 0, bWins = 0, draws = 0;
        foreach (var m in matches)
        {
            var homeIsA = Normalizer.Matches(m.Home, aNorm);
            var aGoals = homeIsA ? m.HomeGoal : m.AwayGoal;
            var bGoals = homeIsA ? m.AwayGoal : m.HomeGoal;
            if (aGoals > bGoals) aWins++;
            else if (aGoals < bGoals) bWins++;
            else draws++;
        }
        return new HeadToHeadResult(Normalizer.Normalize(teamA), Normalizer.Normalize(teamB), matches, aWins, bWins, draws);
    }

    /// <summary>Returns the most recent match between the two teams, or null.</summary>
    public MatchRecord? LastMatchBetween(string teamA, string teamB)
    {
        return HeadToHead(teamA, teamB).Matches.FirstOrDefault();
    }

    /// <summary>Returns matches where the named team participated, newest first.</summary>
    public List<MatchRecord> MatchesForTeam(string team) => SearchMatches(team: team);

    private bool TeamInvolved(MatchRecord m, string query)
        => Normalizer.Matches(m.Home, query) || Normalizer.Matches(m.Away, query);

    private static bool AreDistinct(string a, string b) => !string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
}

/// <summary>Result of a head-to-head comparison.</summary>
public sealed record HeadToHeadResult(
    string TeamA,
    string TeamB,
    IReadOnlyList<MatchRecord> Matches,
    int TeamAWins,
    int TeamBWins,
    int Draws)
{
    public int TotalMatches => Matches.Count;
}
