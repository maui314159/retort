using BrazilianSoccerCore.Data;
using BrazilianSoccerCore.Models;

namespace BrazilianSoccerCore.Queries;

/// <summary>Competition-level queries: standings, champions, relegation.</summary>
public sealed class CompetitionQueryEngine
{
    private readonly IReadOnlyList<Match> _matches;

    public CompetitionQueryEngine(IReadOnlyList<Match> matches) => _matches = matches;

    /// <summary>
    /// Compute league-style standings (3-1-0 points) for a competition + season,
    /// using only round-robin match data (Brasileirão sources).
    /// </summary>
    public List<StandingsRow> Standings(string competition, int season)
    {
        var compKey = competition.ToLowerInvariant();
        var rows = new Dictionary<string, StandingsAccumulator>(StringComparer.Ordinal);

        foreach (var m in _matches)
        {
            if (m.Season != season) continue;
            if (!m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) continue;
            if (m.HomeGoal is null || m.AwayGoal is null) continue;

            var homeKey = TeamNormalizer.Key(m.HomeTeam);
            var awayKey = TeamNormalizer.Key(m.AwayTeam);

            var home = rows.GetOrAdd(homeKey, () => new StandingsAccumulator(m.HomeTeam));
            var away = rows.GetOrAdd(awayKey, () => new StandingsAccumulator(m.AwayTeam));

            home.Matches++; away.Matches++;
            home.GoalsFor += m.HomeGoal.Value; home.GoalsAgainst += m.AwayGoal.Value;
            away.GoalsFor += m.AwayGoal.Value; away.GoalsAgainst += m.HomeGoal.Value;

            if (m.HomeGoal > m.AwayGoal)
            {
                home.Wins++; home.Points += 3; away.Losses++;
            }
            else if (m.HomeGoal < m.AwayGoal)
            {
                away.Wins++; away.Points += 3; home.Losses++;
            }
            else
            {
                home.Draws++; away.Draws++; home.Points++; away.Points++;
            }
        }

        return rows.Values
            .OrderByDescending(a => a.Points)
            .ThenByDescending(a => a.Wins)
            .ThenByDescending(a => a.GoalsFor - a.GoalsAgainst)
            .ThenByDescending(a => a.GoalsFor)
            .Select((a, i) => new StandingsRow
            {
                Position = i + 1,
                Team = a.Display,
                Points = a.Points,
                Wins = a.Wins,
                Draws = a.Draws,
                Losses = a.Losses,
                GoalsFor = a.GoalsFor,
                GoalsAgainst = a.GoalsAgainst,
                GoalDifference = a.GoalsFor - a.GoalsAgainst,
                Matches = a.Matches,
            })
            .ToList();
    }

    /// <summary>Champion (top of standings) for a competition+season.</summary>
    public StandingsRow? Champion(string competition, int season)
        => Standings(competition, season).FirstOrDefault();

    /// <summary>Bottom N teams in the standings (relegation zone).</summary>
    public List<StandingsRow> Relegated(string competition, int season, int count = 4)
        => Standings(competition, season).TakeLast(count).ToList();

    /// <summary>Top scorers by team goals — a proxy since the dataset has no per-player scorers.</summary>
    public List<(string Team, int Goals)> TopScoringTeams(string competition, int season, int limit = 10)
    {
        var goalsByTeam = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var m in _matches)
        {
            if (m.Season != season) continue;
            if (!m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) continue;
            if (m.HomeGoal is null || m.AwayGoal is null) continue;

            var homeKey = TeamNormalizer.Key(m.HomeTeam);
            var awayKey = TeamNormalizer.Key(m.AwayTeam);
            goalsByTeam[homeKey] = goalsByTeam.GetValueOrDefault(homeKey) + m.HomeGoal.Value;
            goalsByTeam[awayKey] = goalsByTeam.GetValueOrDefault(awayKey) + m.AwayGoal.Value;
        }

        return goalsByTeam
            .OrderByDescending(kv => kv.Value)
            .Take(limit)
            .Select(kv => (kv.Key, kv.Value))
            .ToList();
    }

    /// <summary>All seasons present in a competition.</summary>
    public List<int> SeasonsInCompetition(string competition)
        => _matches
            .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) && m.Season is not null)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();

    private sealed class StandingsAccumulator
    {
        public string Display { get; }
        public int Points { get; set; }
        public int Wins { get; set; }
        public int Draws { get; set; }
        public int Losses { get; set; }
        public int GoalsFor { get; set; }
        public int GoalsAgainst { get; set; }
        public int Matches { get; set; }

        public StandingsAccumulator(string display) => Display = display;
    }
}

internal static class DictExtensions
{
    public static TValue GetOrAdd<TKey, TValue>(
        this Dictionary<TKey, TValue> dict, TKey key, Func<TValue> factory) where TKey : notnull
    {
        if (!dict.TryGetValue(key, out var val))
        {
            val = factory();
            dict[key] = val;
        }
        return val;
    }

    public static int GetValueOrDefault<TKey>(this Dictionary<TKey, int> dict, TKey key) where TKey : notnull
        => dict.TryGetValue(key, out var v) ? v : 0;
}