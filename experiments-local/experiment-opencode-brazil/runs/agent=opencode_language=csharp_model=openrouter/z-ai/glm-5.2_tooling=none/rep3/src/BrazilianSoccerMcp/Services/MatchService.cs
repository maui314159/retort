using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Provides match-level queries: filtering by team, opponent, competition,
/// season and date range, plus head-to-head comparisons.
/// </summary>
public sealed class MatchService
{
    private readonly IReadOnlyList<MatchRecord> _matches;

    public MatchService(DataRepository repo)
    {
        _matches = repo.Matches;
    }

    /// <summary>Filters matches by the supplied (all optional) criteria.</summary>
    public IReadOnlyList<MatchRecord> Search(
        string? team = null,
        string? opponent = null,
        string? competition = null,
        int? season = null,
        DateTime? from = null,
        DateTime? to = null)
    {
        var teamKey = TeamNameNormalizer.NormalizeKey(team ?? "");
        var oppKey = TeamNameNormalizer.NormalizeKey(opponent ?? "");
        var compKey = (competition ?? "").Trim();
        bool compFilter = !string.IsNullOrEmpty(compKey);

        var result = new List<MatchRecord>();
        foreach (var m in _matches)
        {
            if (compFilter && !CompetitionMatches(m.Competition, compKey)) continue;
            if (season.HasValue && m.Season != season.Value) continue;
            if (from.HasValue && m.Date < from.Value) continue;
            if (to.HasValue && m.Date > to.Value) continue;

            if (!string.IsNullOrEmpty(teamKey))
            {
                var homeKey = TeamNameNormalizer.NormalizeKey(m.HomeTeam);
                var awayKey = TeamNameNormalizer.NormalizeKey(m.AwayTeam);
                bool teamIsHome = homeKey == teamKey;
                bool teamIsAway = awayKey == teamKey;
                if (!teamIsHome && !teamIsAway) continue;

                if (!string.IsNullOrEmpty(oppKey))
                {
                    bool oppMatch = (teamIsHome && awayKey == oppKey) || (teamIsAway && homeKey == oppKey);
                    if (!oppMatch) continue;
                }
            }
            else if (!string.IsNullOrEmpty(oppKey))
            {
                // No team specified but opponent is - any match involving opponent.
                if (TeamNameNormalizer.NormalizeKey(m.HomeTeam) != oppKey &&
                    TeamNameNormalizer.NormalizeKey(m.AwayTeam) != oppKey) continue;
            }

            result.Add(m);
        }
        result.Sort((a, b) => a.Date.CompareTo(b.Date));
        return result;
    }

    /// <summary>Head-to-head record between two teams.</summary>
    public HeadToHeadResult HeadToHead(string teamA, string teamB)
    {
        var keyA = TeamNameNormalizer.NormalizeKey(teamA);
        var keyB = TeamNameNormalizer.NormalizeKey(teamB);
        int winsA = 0, winsB = 0, draws = 0;
        var matches = new List<MatchRecord>();
        foreach (var m in _matches)
        {
            var hk = TeamNameNormalizer.NormalizeKey(m.HomeTeam);
            var ak = TeamNameNormalizer.NormalizeKey(m.AwayTeam);
            if ((hk == keyA && ak == keyB) || (hk == keyB && ak == keyA))
            {
                matches.Add(m);
                if (m.HomeGoal > m.AwayGoal)
                {
                    if (hk == keyA) winsA++; else winsB++;
                }
                else if (m.HomeGoal < m.AwayGoal)
                {
                    if (hk == keyA) winsB++; else winsA++;
                }
                else draws++;
            }
        }
        matches.Sort((a, b) => a.Date.CompareTo(b.Date));
        return new HeadToHeadResult(teamA, teamB, winsA, winsB, draws, matches);
    }

    /// <summary>Matches the competition tag loosely so "Brasileirao" matches both
    /// "Brasileirao" and "BrasileiraoHistorico" if requested.</summary>
    private static bool CompetitionMatches(string actual, string requested)
    {
        if (string.Equals(actual, requested, StringComparison.OrdinalIgnoreCase)) return true;
        if (requested.Equals("Brasileirao", StringComparison.OrdinalIgnoreCase)
            && actual.StartsWith("Brasileirao", StringComparison.OrdinalIgnoreCase))
            return true;
        return actual.Contains(requested, StringComparison.OrdinalIgnoreCase);
    }
}

public sealed record HeadToHeadResult(
    string TeamA,
    string TeamB,
    int WinsA,
    int WinsB,
    int Draws,
    IReadOnlyList<MatchRecord> Matches);
