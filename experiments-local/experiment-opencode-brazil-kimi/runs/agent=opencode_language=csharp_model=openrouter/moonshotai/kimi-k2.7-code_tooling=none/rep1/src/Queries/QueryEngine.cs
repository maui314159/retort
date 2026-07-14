/*
 * Brazilian Soccer MCP Server - Query Engine
 *
 * Implements the required query capabilities: match, team, player,
 * competition and statistical queries. All team name comparisons use
 * normalized names so queries work across every dataset.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Queries;

public sealed class QueryEngine
{
    private readonly DataRepository _repository;

    public QueryEngine(DataRepository repository)
    {
        _repository = repository;
    }

    public IReadOnlyList<MatchRecord> FindMatches(
        string? team = null,
        string? opponent = null,
        int? season = null,
        string? competition = null,
        DateTime? dateFrom = null,
        DateTime? dateTo = null)
    {
        var normalizedTeam = TeamNameNormalizer.Normalize(team ?? string.Empty);
        var normalizedOpponent = TeamNameNormalizer.Normalize(opponent ?? string.Empty);
        var normalizedCompetition = NormalizeCompetition(competition);

        return _repository.Matches.Where(m =>
        {
            var home = TeamNameNormalizer.Normalize(m.HomeTeam);
            var away = TeamNameNormalizer.Normalize(m.AwayTeam);

            if (!string.IsNullOrEmpty(normalizedTeam))
            {
                if (home != normalizedTeam && away != normalizedTeam)
                    return false;
            }

            if (!string.IsNullOrEmpty(normalizedOpponent))
            {
                if (home != normalizedOpponent && away != normalizedOpponent)
                    return false;
                if (!string.IsNullOrEmpty(normalizedTeam))
                {
                    if (!((home == normalizedTeam && away == normalizedOpponent) ||
                          (home == normalizedOpponent && away == normalizedTeam)))
                        return false;
                }
            }

            if (season.HasValue && m.Season != season.Value)
                return false;

            if (!string.IsNullOrEmpty(normalizedCompetition) &&
                NormalizeCompetition(m.Competition) != normalizedCompetition)
                return false;

            if (dateFrom.HasValue && (!m.Date.HasValue || m.Date.Value.Date < dateFrom.Value.Date))
                return false;

            if (dateTo.HasValue && (!m.Date.HasValue || m.Date.Value.Date > dateTo.Value.Date))
                return false;

            return true;
        }).OrderByDescending(m => m.Date).ToList();
    }

    public TeamStatistics GetTeamStatistics(
        string team,
        int? season = null,
        string? competition = null,
        bool homeOnly = false,
        bool awayOnly = false)
    {
        var normalizedTeam = TeamNameNormalizer.Normalize(team);
        var normalizedCompetition = NormalizeCompetition(competition);

        var matches = _repository.Matches.Where(m =>
        {
            var home = TeamNameNormalizer.Normalize(m.HomeTeam);
            var away = TeamNameNormalizer.Normalize(m.AwayTeam);

            bool involves = home == normalizedTeam || away == normalizedTeam;
            if (!involves) return false;

            if (homeOnly && home != normalizedTeam) return false;
            if (awayOnly && away != normalizedTeam) return false;
            if (season.HasValue && m.Season != season.Value) return false;
            if (!string.IsNullOrEmpty(normalizedCompetition) && NormalizeCompetition(m.Competition) != normalizedCompetition)
                return false;

            return true;
        }).ToList();

        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
        foreach (var match in matches)
        {
            var home = TeamNameNormalizer.Normalize(match.HomeTeam);
            var away = TeamNameNormalizer.Normalize(match.AwayTeam);
            var isHome = home == normalizedTeam;
            var teamGoals = isHome ? match.HomeGoals : match.AwayGoals;
            var oppGoals = isHome ? match.AwayGoals : match.HomeGoals;

            if (!teamGoals.HasValue || !oppGoals.HasValue) continue;

            goalsFor += teamGoals.Value;
            goalsAgainst += oppGoals.Value;

            if (teamGoals.Value > oppGoals.Value) wins++;
            else if (teamGoals.Value == oppGoals.Value) draws++;
            else losses++;
        }

        return new TeamStatistics
        {
            Team = team,
            Matches = wins + draws + losses,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = goalsFor,
            GoalsAgainst = goalsAgainst
        };
    }

    public HeadToHeadRecord GetHeadToHead(string teamA, string teamB)
    {
        var normA = TeamNameNormalizer.Normalize(teamA);
        var normB = TeamNameNormalizer.Normalize(teamB);

        var matches = _repository.Matches.Where(m =>
        {
            var home = TeamNameNormalizer.Normalize(m.HomeTeam);
            var away = TeamNameNormalizer.Normalize(m.AwayTeam);
            return (home == normA && away == normB) || (home == normB && away == normA);
        }).ToList();

        int aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
        foreach (var match in matches)
        {
            if (!match.HomeGoals.HasValue || !match.AwayGoals.HasValue) continue;
            var home = TeamNameNormalizer.Normalize(match.HomeTeam);
            var away = TeamNameNormalizer.Normalize(match.AwayTeam);

            if (home == normA)
            {
                aGoals += match.HomeGoals.Value;
                bGoals += match.AwayGoals.Value;
                if (match.HomeGoals.Value > match.AwayGoals.Value) aWins++;
                else if (match.HomeGoals.Value < match.AwayGoals.Value) bWins++;
                else draws++;
            }
            else
            {
                aGoals += match.AwayGoals.Value;
                bGoals += match.HomeGoals.Value;
                if (match.AwayGoals.Value > match.HomeGoals.Value) aWins++;
                else if (match.AwayGoals.Value < match.HomeGoals.Value) bWins++;
                else draws++;
            }
        }

        return new HeadToHeadRecord
        {
            TeamA = teamA,
            TeamB = teamB,
            Matches = aWins + bWins + draws,
            TeamAWins = aWins,
            TeamBWins = bWins,
            Draws = draws,
            TeamAGoals = aGoals,
            TeamBGoals = bGoals
        };
    }

    public IReadOnlyList<PlayerRecord> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? maxOverall = null)
    {
        return _repository.Players.Where(p =>
        {
            if (!string.IsNullOrWhiteSpace(name))
            {
                if (p.Name == null || !p.Name.Contains(name, StringComparison.OrdinalIgnoreCase))
                    return false;
            }
            if (!string.IsNullOrWhiteSpace(nationality))
            {
                if (p.Nationality == null || !p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase))
                    return false;
            }
            if (!string.IsNullOrWhiteSpace(club))
            {
                if (p.Club == null || !p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
                    return false;
            }
            if (!string.IsNullOrWhiteSpace(position))
            {
                if (p.Position == null || !p.Position.Contains(position, StringComparison.OrdinalIgnoreCase))
                    return false;
            }
            if (minOverall.HasValue && (!p.Overall.HasValue || p.Overall.Value < minOverall.Value))
                return false;
            if (maxOverall.HasValue && (!p.Overall.HasValue || p.Overall.Value > maxOverall.Value))
                return false;
            return true;
        }).ToList();
    }

    public IReadOnlyList<PlayerRecord> GetTopPlayers(
        string? nationality = null,
        string? club = null,
        string? position = null,
        int count = 10)
    {
        var query = _repository.Players.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(nationality))
            query = query.Where(p => p.Nationality != null && p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(club))
            query = query.Where(p => p.Club != null && p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p => p.Position != null && p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));

        return query.Where(p => p.Overall.HasValue)
            .OrderByDescending(p => p.Overall!.Value)
            .Take(count)
            .ToList();
    }

    public IReadOnlyList<StandingRow> GetCompetitionStandings(int season, string competition)
    {
        var normalizedCompetition = NormalizeCompetition(competition);
        var matches = _repository.Matches
            .Where(m => m.Season == season && NormalizeCompetition(m.Competition) == normalizedCompetition)
            .ToList();

        var table = new Dictionary<string, StandingRow>(StringComparer.OrdinalIgnoreCase);
        foreach (var match in matches)
        {
            if (!match.HomeGoals.HasValue || !match.AwayGoals.HasValue) continue;
            table.TryAdd(match.HomeTeam, new StandingRow { Team = match.HomeTeam });
            table.TryAdd(match.AwayTeam, new StandingRow { Team = match.AwayTeam });

            var home = table[match.HomeTeam];
            var away = table[match.AwayTeam];

            if (match.HomeGoals.Value > match.AwayGoals.Value)
            {
                home = home with { Wins = home.Wins + 1, Points = home.Points + 3 };
                away = away with { Losses = away.Losses + 1 };
            }
            else if (match.HomeGoals.Value < match.AwayGoals.Value)
            {
                away = away with { Wins = away.Wins + 1, Points = away.Points + 3 };
                home = home with { Losses = home.Losses + 1 };
            }
            else
            {
                home = home with { Draws = home.Draws + 1, Points = home.Points + 1 };
                away = away with { Draws = away.Draws + 1, Points = away.Points + 1 };
            }

            home = home with { GoalsFor = home.GoalsFor + match.HomeGoals.Value, GoalsAgainst = home.GoalsAgainst + match.AwayGoals.Value };
            away = away with { GoalsFor = away.GoalsFor + match.AwayGoals.Value, GoalsAgainst = away.GoalsAgainst + match.HomeGoals.Value };

            table[match.HomeTeam] = home;
            table[match.AwayTeam] = away;
        }

        return table.Values
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ToList();
    }

    public IReadOnlyList<string> GetTeamCompetitions(string team)
    {
        var normalizedTeam = TeamNameNormalizer.Normalize(team);
        return _repository.Matches
            .Where(m => TeamNameNormalizer.Normalize(m.HomeTeam) == normalizedTeam || TeamNameNormalizer.Normalize(m.AwayTeam) == normalizedTeam)
            .Select(m => m.Competition)
            .Distinct()
            .OrderBy(c => c)
            .ToList();
    }

    public IReadOnlyList<MatchRecord> GetBiggestWins(string? competition = null, int count = 10)
    {
        var normalizedCompetition = NormalizeCompetition(competition);
        return _repository.Matches
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .Where(m => string.IsNullOrEmpty(normalizedCompetition) || NormalizeCompetition(m.Competition) == normalizedCompetition)
            .Select(m => new { Match = m, Diff = Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value) })
            .Where(x => x.Diff > 0)
            .OrderByDescending(x => x.Diff)
            .ThenByDescending(x => x.Match.Date)
            .Take(count)
            .Select(x => x.Match)
            .ToList();
    }

    public double GetAverageGoalsPerMatch(string? competition = null)
    {
        var normalizedCompetition = NormalizeCompetition(competition);
        var matches = _repository.Matches
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .Where(m => string.IsNullOrEmpty(normalizedCompetition) || NormalizeCompetition(m.Competition) == normalizedCompetition)
            .ToList();

        if (matches.Count == 0) return 0;
        return matches.Average(m => m.HomeGoals!.Value + m.AwayGoals!.Value);
    }

    public TeamStatistics GetBestAwayRecord(string? competition = null, int? season = null)
    {
        var normalizedCompetition = NormalizeCompetition(competition);
        var awayTeams = _repository.Matches
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .Where(m => string.IsNullOrEmpty(normalizedCompetition) || NormalizeCompetition(m.Competition) == normalizedCompetition)
            .Where(m => !season.HasValue || m.Season == season.Value)
            .GroupBy(m => TeamNameNormalizer.Normalize(m.AwayTeam))
            .Select(g => new
            {
                Team = g.First().AwayTeam,
                Stats = new TeamStatistics
                {
                    Team = g.First().AwayTeam,
                    Matches = g.Count(),
                    Wins = g.Count(m => m.AwayGoals!.Value > m.HomeGoals!.Value),
                    Draws = g.Count(m => m.AwayGoals!.Value == m.HomeGoals!.Value),
                    Losses = g.Count(m => m.AwayGoals!.Value < m.HomeGoals!.Value),
                    GoalsFor = g.Sum(m => m.AwayGoals!.Value),
                    GoalsAgainst = g.Sum(m => m.HomeGoals!.Value)
                }
            })
            .OrderByDescending(x => x.Stats.WinRate)
            .ThenByDescending(x => x.Stats.Points)
            .FirstOrDefault();

        return awayTeams?.Stats ?? new TeamStatistics { Team = string.Empty };
    }

    public IReadOnlyList<StandingRow> GetTopScorersByTeam(int season, string competition)
    {
        // Aggregate goals scored by team; individual scorers are not available.
        return GetCompetitionStandings(season, competition)
            .OrderByDescending(r => r.GoalsFor)
            .Take(10)
            .ToList();
    }

    private static string NormalizeCompetition(string? competition)
    {
        if (string.IsNullOrWhiteSpace(competition)) return string.Empty;
        var normalized = competition.Trim().ToLowerInvariant();
        if (normalized.Contains("brasileir") || normalized.Contains("serie a") || normalized.Contains("campeonato brasileiro"))
            return "brasileirão";
        if (normalized.Contains("copa do brasil") || normalized.Contains("brazilian cup"))
            return "copa do brasil";
        if (normalized.Contains("libertadores") || normalized.Contains("copa libertadores"))
            return "copa libertadores";
        return normalized;
    }
}
