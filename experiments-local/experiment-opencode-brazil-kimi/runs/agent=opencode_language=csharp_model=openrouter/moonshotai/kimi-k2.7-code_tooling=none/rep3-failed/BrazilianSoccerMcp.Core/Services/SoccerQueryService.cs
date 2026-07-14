// <copyright file="SoccerQueryService.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Business logic for match, team, player and competition queries.
// </copyright>
using System.Globalization;
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;

namespace BrazilianSoccerMcp.Core.Services;

/// <summary>
/// Provides querying and aggregation capabilities over the loaded soccer datasets.
/// </summary>
public sealed class SoccerQueryService
{
    private readonly SoccerDataContext _context;

    public SoccerQueryService(SoccerDataContext context)
    {
        _context = context ?? throw new ArgumentNullException(nameof(context));
    }

    #region Matches

    /// <summary>
    /// Searches for matches using the supplied criteria.
    /// </summary>
    public IReadOnlyList<SoccerMatch> SearchMatches(MatchSearchCriteria criteria)
    {
        var query = _context.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(criteria.Team))
        {
            var team = TeamNameNormalizer.Normalize(criteria.Team);
            query = query.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, team) ||
                TeamNameNormalizer.Matches(m.AwayTeam, team));
        }

        if (!string.IsNullOrWhiteSpace(criteria.Opponent))
        {
            var opponent = TeamNameNormalizer.Normalize(criteria.Opponent);
            query = query.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, opponent) ||
                TeamNameNormalizer.Matches(m.AwayTeam, opponent));
        }

        if (criteria.StartDate.HasValue)
            query = query.Where(m => m.Date >= criteria.StartDate.Value);

        if (criteria.EndDate.HasValue)
            query = query.Where(m => m.Date <= criteria.EndDate.Value);

        if (!string.IsNullOrWhiteSpace(criteria.Competition))
        {
            var comp = criteria.Competition;
            query = query.Where(m => CompetitionCatalog.Matches(m.Competition, comp));
        }

        if (criteria.Season.HasValue)
            query = query.Where(m => m.Season == criteria.Season.Value);

        if (!string.IsNullOrWhiteSpace(criteria.Round))
        {
            var round = criteria.Round;
            query = query.Where(m =>
                !string.IsNullOrWhiteSpace(m.Round) &&
                m.Round.Contains(round, StringComparison.OrdinalIgnoreCase));
        }

        var sorted = ApplyMatchSort(query, criteria.SortBy);

        if (criteria.Limit.HasValue && criteria.Limit.Value > 0)
            sorted = sorted.Take(criteria.Limit.Value);

        return sorted.ToList();
    }

    /// <summary>
    /// Returns head-to-head matches between two teams, ordered by descending date.
    /// </summary>
    public IReadOnlyList<SoccerMatch> GetHeadToHead(string teamA, string teamB, int? season = null)
    {
        var normalizedA = TeamNameNormalizer.Normalize(teamA);
        var normalizedB = TeamNameNormalizer.Normalize(teamB);

        var query = _context.Matches
            .Where(m => m.Involves(normalizedA) && m.Involves(normalizedB));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        return query
            .OrderByDescending(m => m.Date)
            .ToList();
    }

    /// <summary>
    /// Returns the most recent match between two teams.
    /// </summary>
    public SoccerMatch? GetMostRecentMatch(string teamA, string teamB)
    {
        return GetHeadToHead(teamA, teamB).FirstOrDefault();
    }

    #endregion

    #region Team Statistics

    /// <summary>
    /// Computes overall team statistics for the supplied team and optional season/competition.
    /// </summary>
    public TeamStatistics GetTeamStatistics(string team, int? season = null, string? competition = null)
    {
        var normalizedTeam = TeamNameNormalizer.Normalize(team);
        var matches = MatchesForTeam(normalizedTeam, season, competition)
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        var stats = new TeamStatisticsBuilder(team, season);
        foreach (var m in matches)
        {
            stats.AddMatch(m);
        }

        return stats.Build();
    }

    /// <summary>
    /// Computes home/away split statistics for a team.
    /// </summary>
    public TeamVenueStatistics GetTeamVenueStatistics(string team, int? season = null, string? competition = null)
    {
        var normalizedTeam = TeamNameNormalizer.Normalize(team);
        var matches = MatchesForTeam(normalizedTeam, season, competition)
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        var homeBuilder = new TeamStatisticsBuilder(team, season);
        var awayBuilder = new TeamStatisticsBuilder(team, season);
        var overallBuilder = new TeamStatisticsBuilder(team, season);

        foreach (var m in matches)
        {
            overallBuilder.AddMatch(m);
            var isHome = TeamNameNormalizer.Matches(m.HomeTeam, normalizedTeam);
            if (isHome)
                homeBuilder.AddMatchAsHome(m);
            else
                awayBuilder.AddMatchAsAway(m);
        }

        return new TeamVenueStatistics
        {
            Team = team,
            Home = homeBuilder.Build(),
            Away = awayBuilder.Build(),
            Overall = overallBuilder.Build()
        };
    }

    /// <summary>
    /// Returns a list of teams ordered by the best away records.
    /// </summary>
    public IReadOnlyList<TeamStatistics> GetBestAwayRecords(int? season = null, string? competition = null, int minMatches = 10)
    {
        var teams = _context.Matches
            .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Where(t => !string.IsNullOrWhiteSpace(t));

        return teams
            .Select(t => GetTeamVenueStatistics(t, season, competition))
            .Where(v => v.Away.Matches >= minMatches)
            .OrderByDescending(v => v.Away.WinRate)
            .ThenByDescending(v => v.Away.GoalsForPerMatch - v.Away.GoalsAgainstPerMatch)
            .Select(v => v.Away)
            .ToList();
    }

    /// <summary>
    /// Computes head-to-head statistics between two teams.
    /// </summary>
    public (int TeamAWins, int Draws, int TeamBWins) GetHeadToHeadStats(string teamA, string teamB)
    {
        var matches = GetHeadToHead(teamA, teamB)
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        var normalizedA = TeamNameNormalizer.Normalize(teamA);
        var normalizedB = TeamNameNormalizer.Normalize(teamB);

        int aWins = 0, draws = 0, bWins = 0;
        foreach (var m in matches)
        {
            var outcome = m.OutcomeFor(normalizedA);
            if (outcome == MatchOutcome.Win) aWins++;
            else if (outcome == MatchOutcome.Draw) draws++;
            else bWins++;
        }

        return (aWins, draws, bWins);
    }

    #endregion

    #region Players

    /// <summary>
    /// Searches players using the supplied criteria.
    /// </summary>
    public IReadOnlyList<Player> SearchPlayers(PlayerSearchCriteria criteria)
    {
        var query = _context.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(criteria.Name))
        {
            var name = criteria.Name;
            query = query.Where(p =>
                p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(criteria.Nationality))
        {
            var nationality = criteria.Nationality;
            query = query.Where(p =>
                p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(criteria.Club))
        {
            var club = TeamNameNormalizer.Normalize(criteria.Club);
            query = query.Where(p =>
                TeamNameNormalizer.Matches(p.Club, club));
        }

        if (!string.IsNullOrWhiteSpace(criteria.Position))
        {
            var position = criteria.Position;
            query = query.Where(p =>
                p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }

        if (criteria.MinOverall.HasValue)
            query = query.Where(p => p.Overall.HasValue && p.Overall.Value >= criteria.MinOverall.Value);

        var sorted = criteria.SortBy?.ToLowerInvariant() switch
        {
            "name_asc" => query.OrderBy(p => p.Name),
            _ => query.OrderByDescending(p => p.Overall ?? 0).ThenBy(p => p.Name)
        };

        var result = sorted.ToList();
        if (criteria.Limit.HasValue && criteria.Limit.Value > 0)
            result = result.Take(criteria.Limit.Value).ToList();

        return result;
    }

    #endregion

    #region Competitions

    /// <summary>
    /// Calculates a league table from match results for a given competition and season.
    /// </summary>
    public IReadOnlyList<CompetitionStanding> GetStandings(string competition, int season)
    {
        var matches = _context.Matches
            .Where(m => CompetitionCatalog.Matches(m.Competition, competition))
            .Where(m => m.Season == season)
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        var table = new Dictionary<string, StandingBuilder>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            table.TryAdd(m.HomeTeam, new StandingBuilder(m.HomeTeam));
            table.TryAdd(m.AwayTeam, new StandingBuilder(m.AwayTeam));

            table[m.HomeTeam].AddHome(m.HomeGoals!.Value, m.AwayGoals!.Value);
            table[m.AwayTeam].AddAway(m.AwayGoals!.Value, m.HomeGoals!.Value);
        }

        return table.Values
            .Select(s => s.Build())
            .OrderByDescending(s => s.Points)
            .ThenByDescending(s => s.GoalDifference)
            .ThenByDescending(s => s.GoalsFor)
            .ThenBy(s => s.Team)
            .ToList();
    }

    /// <summary>
    /// Returns the biggest wins (by absolute goal difference) for a given competition.
    /// </summary>
    public IReadOnlyList<SoccerMatch> GetBiggestWins(string? competition = null, int limit = 10, int? season = null)
    {
        var query = _context.Matches
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => CompetitionCatalog.Matches(m.Competition, competition));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        return query
            .OrderByDescending(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value))
            .ThenByDescending(m => m.HomeGoals!.Value + m.AwayGoals!.Value)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Returns aggregate statistics for a competition/season.
    /// </summary>
    public CompetitionStatistics GetCompetitionStatistics(string? competition = null, int? season = null)
    {
        var query = _context.Matches
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => CompetitionCatalog.Matches(m.Competition, competition));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        var matches = query.ToList();
        var totalGoals = matches.Sum(m => m.HomeGoals!.Value + m.AwayGoals!.Value);

        return new CompetitionStatistics
        {
            MatchesPlayed = matches.Count,
            TotalGoals = totalGoals,
            AverageGoalsPerMatch = matches.Count == 0 ? 0 : 1.0 * totalGoals / matches.Count,
            HomeWins = matches.Count(m => m.HomeGoals!.Value > m.AwayGoals!.Value),
            Draws = matches.Count(m => m.HomeGoals!.Value == m.AwayGoals!.Value),
            AwayWins = matches.Count(m => m.HomeGoals!.Value < m.AwayGoals!.Value)
        };
    }

    #endregion

    #region Helpers

    private IEnumerable<SoccerMatch> MatchesForTeam(string team, int? season, string? competition)
    {
        var query = _context.Matches
            .Where(m => m.Involves(team))
            .AsEnumerable();

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => CompetitionCatalog.Matches(m.Competition, competition));

        return query;
    }

    private static IEnumerable<SoccerMatch> ApplyMatchSort(IEnumerable<SoccerMatch> query, string? sortBy)
    {
        return sortBy?.ToLowerInvariant() switch
        {
            "date_asc" => query.OrderBy(m => m.Date),
            "goal_diff_desc" => query
                .OrderByDescending(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue
                    ? Math.Abs(m.HomeGoals.Value - m.AwayGoals.Value)
                    : 0),
            _ => query.OrderByDescending(m => m.Date)
        };
    }

    #endregion
}

/// <summary>
/// Aggregate statistics for a competition.
/// </summary>
public sealed class CompetitionStatistics
{
    public int MatchesPlayed { get; init; }
    public int TotalGoals { get; init; }
    public double AverageGoalsPerMatch { get; init; }
    public int HomeWins { get; init; }
    public int Draws { get; init; }
    public int AwayWins { get; init; }

    public double HomeWinRate => MatchesPlayed == 0 ? 0 : 100.0 * HomeWins / MatchesPlayed;
    public double DrawRate => MatchesPlayed == 0 ? 0 : 100.0 * Draws / MatchesPlayed;
    public double AwayWinRate => MatchesPlayed == 0 ? 0 : 100.0 * AwayWins / MatchesPlayed;
}

/// <summary>
/// Mutable accumulator used to build <see cref="TeamStatistics"/>.
/// </summary>
internal sealed class TeamStatisticsBuilder
{
    private readonly string _team;
    private readonly int? _season;
    private int _matches;
    private int _wins;
    private int _draws;
    private int _losses;
    private int _goalsFor;
    private int _goalsAgainst;

    public TeamStatisticsBuilder(string team, int? season = null)
    {
        _team = team;
        _season = season;
    }

    public void AddMatch(SoccerMatch match)
    {
        var team = TeamNameNormalizer.Normalize(_team);
        var isHome = TeamNameNormalizer.Matches(match.HomeTeam, team);

        if (isHome)
            AddMatchAsHome(match);
        else
            AddMatchAsAway(match);
    }

    public void AddMatchAsHome(SoccerMatch match)
    {
        if (!match.HomeGoals.HasValue || !match.AwayGoals.HasValue)
            return;

        _matches++;
        _goalsFor += match.HomeGoals.Value;
        _goalsAgainst += match.AwayGoals.Value;

        var outcome = match.HomeGoals.Value.CompareTo(match.AwayGoals.Value);
        if (outcome > 0) _wins++;
        else if (outcome < 0) _losses++;
        else _draws++;
    }

    public void AddMatchAsAway(SoccerMatch match)
    {
        if (!match.HomeGoals.HasValue || !match.AwayGoals.HasValue)
            return;

        _matches++;
        _goalsFor += match.AwayGoals.Value;
        _goalsAgainst += match.HomeGoals.Value;

        var outcome = match.AwayGoals.Value.CompareTo(match.HomeGoals.Value);
        if (outcome > 0) _wins++;
        else if (outcome < 0) _losses++;
        else _draws++;
    }

    public TeamStatistics Build()
    {
        return new TeamStatistics
        {
            Team = _team,
            Season = _season,
            Matches = _matches,
            Wins = _wins,
            Draws = _draws,
            Losses = _losses,
            GoalsFor = _goalsFor,
            GoalsAgainst = _goalsAgainst
        };
    }
}

/// <summary>
/// Mutable accumulator used to build <see cref="CompetitionStanding"/>.
/// </summary>
internal sealed class StandingBuilder
{
    private readonly string _team;
    private int _matches;
    private int _wins;
    private int _draws;
    private int _losses;
    private int _goalsFor;
    private int _goalsAgainst;

    public StandingBuilder(string team)
    {
        _team = team;
    }

    public void AddHome(int scored, int conceded)
    {
        _matches++;
        _goalsFor += scored;
        _goalsAgainst += conceded;
        if (scored > conceded) _wins++;
        else if (scored < conceded) _losses++;
        else _draws++;
    }

    public void AddAway(int scored, int conceded)
    {
        _matches++;
        _goalsFor += scored;
        _goalsAgainst += conceded;
        if (scored > conceded) _wins++;
        else if (scored < conceded) _losses++;
        else _draws++;
    }

    public CompetitionStanding Build()
    {
        return new CompetitionStanding
        {
            Team = _team,
            Matches = _matches,
            Wins = _wins,
            Draws = _draws,
            Losses = _losses,
            GoalsFor = _goalsFor,
            GoalsAgainst = _goalsAgainst
        };
    }
}
