using BrazilianSoccerCore.Data;
using BrazilianSoccerCore.Models;

namespace BrazilianSoccerCore.Queries;

/// <summary>Queries over the unified match collection.</summary>
public sealed class MatchQueryEngine
{
    private readonly IReadOnlyList<Match> _matches;

    public MatchQueryEngine(IReadOnlyList<Match> matches) => _matches = matches;

    // ---------- Match search ----------

    /// <summary>Search matches by team, opponent, date range, competition, and/or season.</summary>
    public List<Match> SearchMatches(
        string? team = null,
        string? opponent = null,
        DateTime? fromDate = null,
        DateTime? toDate = null,
        string? competition = null,
        int? season = null,
        int limit = 100)
    {
        var teamKey = team is null ? null : TeamNormalizer.Key(team);
        var oppKey = opponent is null ? null : TeamNormalizer.Key(opponent);

        var q = _matches.AsEnumerable();

        if (teamKey is not null)
            q = q.Where(m => TeamNormalizer.Key(m.HomeTeam) == teamKey || TeamNormalizer.Key(m.AwayTeam) == teamKey);

        if (oppKey is not null)
            q = q.Where(m => TeamNormalizer.Key(m.HomeTeam) == oppKey || TeamNormalizer.Key(m.AwayTeam) == oppKey);

        if (fromDate is not null)
            q = q.Where(m => m.Date >= fromDate);

        if (toDate is not null)
            q = q.Where(m => m.Date <= toDate);

        if (competition is not null)
            q = q.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        if (season is not null)
            q = q.Where(m => m.Season == season);

        return q.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    /// <summary>All matches between two specific teams (either venue), newest first.</summary>
    public List<Match> HeadToHeadMatches(string teamA, string teamB)
    {
        var aKey = TeamNormalizer.Key(teamA);
        var bKey = TeamNormalizer.Key(teamB);
        return _matches
            .Where(m =>
                (TeamNormalizer.Key(m.HomeTeam) == aKey && TeamNormalizer.Key(m.AwayTeam) == bKey) ||
                (TeamNormalizer.Key(m.HomeTeam) == bKey && TeamNormalizer.Key(m.AwayTeam) == aKey))
            .OrderByDescending(m => m.Date)
            .ToList();
    }

    /// <summary>Most recent match involving the given team.</summary>
    public Match? LastMatch(string team)
    {
        var key = TeamNormalizer.Key(team);
        return _matches
            .Where(m => TeamNormalizer.Key(m.HomeTeam) == key || TeamNormalizer.Key(m.AwayTeam) == key)
            .OrderByDescending(m => m.Date)
            .FirstOrDefault();
    }

    /// <summary>Most recent match between two specific teams.</summary>
    public Match? LastMatchBetween(string teamA, string teamB)
        => HeadToHeadMatches(teamA, teamB).FirstOrDefault();

    // ---------- Head-to-head ----------

    public HeadToHeadResult CompareTeams(string teamA, string teamB)
    {
        var matches = HeadToHeadMatches(teamA, teamB);
        var aKey = TeamNormalizer.Key(teamA);
        var bKey = TeamNormalizer.Key(teamB);

        var aWins = 0;
        var bWins = 0;
        var draws = 0;
        var aGoals = 0;
        var bGoals = 0;

        foreach (var m in matches)
        {
            if (m.HomeGoal is null || m.AwayGoal is null) continue;
            var homeIsA = TeamNormalizer.Key(m.HomeTeam) == aKey;
            var aScore = homeIsA ? m.HomeGoal.Value : m.AwayGoal.Value;
            var bScore = homeIsA ? m.AwayGoal.Value : m.HomeGoal.Value;
            aGoals += aScore;
            bGoals += bScore;
            if (aScore > bScore) aWins++;
            else if (aScore < bScore) bWins++;
            else draws++;
        }

        return new HeadToHeadResult
        {
            TeamA = teamA,
            TeamB = teamB,
            Matches = matches.Count(m => m.HomeGoal is not null && m.AwayGoal is not null),
            TeamAWins = aWins,
            TeamBWins = bWins,
            Draws = draws,
            TeamAGoals = aGoals,
            TeamBGoals = bGoals,
        };
    }

    // ---------- Team statistics ----------

    /// <summary>Compute team record. venue: "home", "away", or null for both.</summary>
    public TeamStats GetTeamStats(
        string team,
        string? venue = null,
        string? competition = null,
        int? season = null)
    {
        var key = TeamNormalizer.Key(team);
        var relevant = _matches.Where(m =>
            (TeamNormalizer.Key(m.HomeTeam) == key && venue is null or "home") ||
            (TeamNormalizer.Key(m.AwayTeam) == key && venue is null or "away"));

        if (competition is not null)
            relevant = relevant.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season is not null)
            relevant = relevant.Where(m => m.Season == season);

        var wins = 0;
        var draws = 0;
        var losses = 0;
        var goalsFor = 0;
        var goalsAgainst = 0;
        var count = 0;

        foreach (var m in relevant)
        {
            if (m.HomeGoal is null || m.AwayGoal is null) continue;
            var isHome = TeamNormalizer.Key(m.HomeTeam) == key;
            var teamGoals = isHome ? m.HomeGoal.Value : m.AwayGoal.Value;
            var oppGoals = isHome ? m.AwayGoal.Value : m.HomeGoal.Value;
            goalsFor += teamGoals;
            goalsAgainst += oppGoals;
            count++;
            if (teamGoals > oppGoals) wins++;
            else if (teamGoals < oppGoals) losses++;
            else draws++;
        }

        return new TeamStats
        {
            Team = team,
            Matches = count,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = goalsFor,
            GoalsAgainst = goalsAgainst,
            Venue = venue,
            Competition = competition,
            Season = season,
        };
    }

    /// <summary>Goals scored by a team (home+away) within a filter.</summary>
    public int GoalsScoredBy(string team, string? competition = null, int? season = null)
    {
        var key = TeamNormalizer.Key(team);
        var q = _matches.Where(m =>
            TeamNormalizer.Key(m.HomeTeam) == key || TeamNormalizer.Key(m.AwayTeam) == key);
        if (competition is not null)
            q = q.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season is not null)
            q = q.Where(m => m.Season == season);

        return q.Sum(m =>
            TeamNormalizer.Key(m.HomeTeam) == key ? (m.HomeGoal ?? 0) : (m.AwayGoal ?? 0));
    }

    /// <summary>Team with the best home win rate (min 10 matches).</summary>
    public TeamStats? BestHomeRecord(string? competition = null, int? season = null)
    {
        var teams = GetAllTeams();
        TeamStats? best = null;
        foreach (var t in teams)
        {
            var s = GetTeamStats(t, "home", competition, season);
            if (s.Matches < 10) continue;
            if (best is null || s.WinRate > best.WinRate)
                best = s;
        }
        return best;
    }

    /// <summary>Team with the best away win rate (min 10 matches).</summary>
    public TeamStats? BestAwayRecord(string? competition = null, int? season = null)
    {
        var teams = GetAllTeams();
        TeamStats? best = null;
        foreach (var t in teams)
        {
            var s = GetTeamStats(t, "away", competition, season);
            if (s.Matches < 10) continue;
            if (best is null || s.WinRate > best.WinRate)
                best = s;
        }
        return best;
    }

    /// <summary>All distinct team display names (normalized).</summary>
    public IReadOnlyList<string> GetAllTeams() =>
        _matches
            .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
            .Distinct()
            .OrderBy(t => t)
            .ToList();

    /// <summary>Competitions a team has appeared in.</summary>
    public List<string> CompetitionsForTeam(string team)
    {
        var key = TeamNormalizer.Key(team);
        return _matches
            .Where(m => TeamNormalizer.Key(m.HomeTeam) == key || TeamNormalizer.Key(m.AwayTeam) == key)
            .Select(m => m.Competition)
            .Distinct()
            .OrderBy(c => c)
            .ToList();
    }

    /// <summary>Biggest victories (by goal difference) across filtered matches.</summary>
    public List<Match> BiggestWins(string? competition = null, int? season = null, int limit = 10)
    {
        var q = _matches.Where(m => m.HomeGoal is not null && m.AwayGoal is not null && m.GoalDifference > 0);
        if (competition is not null)
            q = q.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season is not null)
            q = q.Where(m => m.Season == season);
        return q.OrderByDescending(m => m.GoalDifference).ThenByDescending(m => m.Date).Take(limit).ToList();
    }
}