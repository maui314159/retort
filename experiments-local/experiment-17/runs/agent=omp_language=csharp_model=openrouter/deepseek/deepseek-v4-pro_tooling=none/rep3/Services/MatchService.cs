using System.Text;
using BrazilianSoccerMCP.Models;

namespace BrazilianSoccerMCP.Services;

/// <summary>
/// Match query service: search, team stats, head-to-head comparisons.
/// </summary>
public class MatchService
{
    private readonly List<Match> _matches;

    public MatchService(List<Match> matches) => _matches = matches;

    /// <summary>
    /// Search matches by criteria: team, competition, season, date range, round.
    /// </summary>
    public List<Match> SearchMatches(string? team, string? competition, int? season,
        DateTime? fromDate, DateTime? toDate, string? opponent, string? round, string? stage,
        int limit = 200)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team))
            query = query.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, team) ||
                TeamNameNormalizer.Matches(m.AwayTeam, team));

        if (!string.IsNullOrWhiteSpace(opponent))
            query = query.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, opponent) ||
                TeamNameNormalizer.Matches(m.AwayTeam, opponent));

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (fromDate.HasValue)
            query = query.Where(m => m.Date >= fromDate.Value);

        if (toDate.HasValue)
            query = query.Where(m => m.Date <= toDate.Value);

        if (!string.IsNullOrWhiteSpace(round))
            query = query.Where(m =>
                m.Round != null && m.Round.Contains(round, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(stage))
            query = query.Where(m =>
                m.Stage != null && m.Stage.Contains(stage, StringComparison.OrdinalIgnoreCase));

        return query.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    /// <summary>
    /// Get overall team statistics optionally filtered by competition and season.
    /// </summary>
    public TeamStats GetTeamStats(string team, string? competition = null, int? season = null)
    {
        var matches = _matches.Where(m =>
            TeamNameNormalizer.Matches(m.HomeTeam, team) ||
            TeamNameNormalizer.Matches(m.AwayTeam, team));

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        var matchList = matches.ToList();
        return new TeamStats(team, competition, season, matchList);
    }

    /// <summary>
    /// Get head-to-head record between two teams.
    /// </summary>
    public HeadToHeadResult GetHeadToHead(string team1, string team2)
    {
        var matches = _matches.Where(m =>
            (TeamNameNormalizer.Matches(m.HomeTeam, team1) && TeamNameNormalizer.Matches(m.AwayTeam, team2)) ||
            (TeamNameNormalizer.Matches(m.HomeTeam, team2) && TeamNameNormalizer.Matches(m.AwayTeam, team1)))
            .OrderByDescending(m => m.Date)
            .ToList();

        var result = new HeadToHeadResult
        {
            Team1 = team1,
            Team2 = team2,
            Matches = matches,
            TotalMatches = matches.Count,
        };

        foreach (var m in matches)
        {
            if (m.Winner == "draw")
            {
                result.Draws++;
            }
            else if ((m.Winner == "home" && TeamNameNormalizer.Matches(m.HomeTeam, team1)) ||
                     (m.Winner == "away" && TeamNameNormalizer.Matches(m.AwayTeam, team1)))
            {
                result.Team1Wins++;
            }
            else
            {
                result.Team2Wins++;
            }
        }

        return result;
    }

    /// <summary>
    /// Get biggest wins across all matches (or filtered).
    /// </summary>
    public List<Match> GetBiggestWins(string? competition = null, int limit = 20)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        return query
            .OrderByDescending(m => m.GoalDiff)
            .ThenByDescending(m => m.Date)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Get all competitions present in the data.
    /// </summary>
    public List<string> GetCompetitions()
    {
        return _matches
            .Select(m => m.Competition)
            .Distinct()
            .OrderBy(c => c)
            .ToList();
    }

    /// <summary>
    /// Get all seasons across all data (or per competition).
    /// </summary>
    public List<int> GetSeasons(string? competition = null)
    {
        var query = _matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        return query
            .Select(m => m.Season)
            .Where(s => s.HasValue)
            .Select(s => s!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();
    }

    /// <summary>
    /// Get all teams present in the data.
    /// </summary>
    public List<string> GetTeams(string? competition = null)
    {
        var homeTeams = _matches.AsEnumerable();
        var awayTeams = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            homeTeams = homeTeams.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
            awayTeams = awayTeams.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        return homeTeams.Select(m => m.HomeTeam)
            .Concat(awayTeams.Select(m => m.AwayTeam))
            .Distinct()
            .OrderBy(t => t)
            .ToList();
    }

    /// <summary>
    /// Calculate overall league statistics.
    /// </summary>
    public LeagueStats GetLeagueStats(string? competition = null, int? season = null)
    {
        var query = _matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        var matchList = query.ToList();
        return new LeagueStats(competition, season, matchList);
    }
}

// --- Result types ---

public class TeamStats
{
    public string Team { get; }
    public string? Competition { get; }
    public int? Season { get; }
    public int TotalMatches { get; }
    public int Wins { get; }
    public int Draws { get; }
    public int Losses { get; }
    public int GoalsFor { get; }
    public int GoalsAgainst { get; }
    public int HomeMatches { get; }
    public int HomeWins { get; }
    public int HomeDraws { get; }
    public int HomeLosses { get; }
    public int HomeGoalsFor { get; }
    public int HomeGoalsAgainst { get; }
    public int AwayMatches { get; }
    public int AwayWins { get; }
    public int AwayDraws { get; }
    public int AwayLosses { get; }
    public int AwayGoalsFor { get; }
    public int AwayGoalsAgainst { get; }
    public double WinRate => TotalMatches > 0 ? Math.Round((double)Wins / TotalMatches * 100, 1) : 0;

    public TeamStats(string team, string? competition, int? season, List<Match> matches)
    {
        Team = team;
        Competition = competition;
        Season = season;
        TotalMatches = matches.Count;

        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, team);
            int gf = isHome ? m.HomeGoal : m.AwayGoal;
            int ga = isHome ? m.AwayGoal : m.HomeGoal;
            bool win = (isHome && m.Winner == "home") || (!isHome && m.Winner == "away");
            bool draw = m.Winner == "draw";
            bool loss = (isHome && m.Winner == "away") || (!isHome && m.Winner == "home");

            GoalsFor += gf;
            GoalsAgainst += ga;

            if (isHome)
            {
                HomeMatches++; HomeGoalsFor += gf; HomeGoalsAgainst += ga;
                if (win) HomeWins++;
                else if (draw) HomeDraws++;
                else HomeLosses++;
            }
            else
            {
                AwayMatches++; AwayGoalsFor += gf; AwayGoalsAgainst += ga;
                if (win) AwayWins++;
                else if (draw) AwayDraws++;
                else AwayLosses++;
            }

            if (win) Wins++;
            else if (draw) Draws++;
            else Losses++;
        }
    }
}

public class HeadToHeadResult
{
    public string Team1 { get; set; } = "";
    public string Team2 { get; set; } = "";
    public int TotalMatches { get; set; }
    public int Team1Wins { get; set; }
    public int Team2Wins { get; set; }
    public int Draws { get; set; }
    public List<Match> Matches { get; set; } = new();
}

public class LeagueStats
{
    public string? Competition { get; }
    public int? Season { get; }
    public int TotalMatches { get; }
    public int TotalGoals { get; }
    public double AverageGoalsPerMatch { get; }
    public int HomeWins { get; }
    public int AwayWins { get; }
    public int Draws { get; }
    public double HomeWinRate { get; }
    public double AwayWinRate { get; }
    public double DrawRate { get; }

    public LeagueStats(string? competition, int? season, List<Match> matches)
    {
        Competition = competition;
        Season = season;
        TotalMatches = matches.Count;
        TotalGoals = matches.Sum(m => m.TotalGoals);
        AverageGoalsPerMatch = TotalMatches > 0 ? Math.Round((double)TotalGoals / TotalMatches, 2) : 0;
        HomeWins = matches.Count(m => m.Winner == "home");
        AwayWins = matches.Count(m => m.Winner == "away");
        Draws = matches.Count(m => m.Winner == "draw");
        HomeWinRate = TotalMatches > 0 ? Math.Round((double)HomeWins / TotalMatches * 100, 1) : 0;
        AwayWinRate = TotalMatches > 0 ? Math.Round((double)AwayWins / TotalMatches * 100, 1) : 0;
        DrawRate = TotalMatches > 0 ? Math.Round((double)Draws / TotalMatches * 100, 1) : 0;
    }
}