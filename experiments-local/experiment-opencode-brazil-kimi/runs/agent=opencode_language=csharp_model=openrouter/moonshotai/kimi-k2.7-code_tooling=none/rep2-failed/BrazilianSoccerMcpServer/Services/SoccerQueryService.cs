using System.Text;
using BrazilianSoccerMcpServer.Data;
using BrazilianSoccerMcpServer.Models;

namespace BrazilianSoccerMcpServer.Services;

public sealed class SoccerQueryService(SoccerDataStore store)
{
    public SoccerDataStore Store => store;

    public IReadOnlyList<Match> FindMatches(
        string? team = null,
        string? opponent = null,
        string? competition = null,
        int? season = null,
        DateTime? from = null,
        DateTime? to = null,
        string? round = null,
        string? stage = null,
        int? limit = null)
    {
        var normalizedTeam = NameNormalizer.Normalize(team);
        var normalizedOpponent = NameNormalizer.Normalize(opponent);
        var normalizedComp = string.IsNullOrWhiteSpace(competition) ? null : NormalizeCompetition(competition);

        var query = store.Matches.AsEnumerable();

        if (!string.IsNullOrEmpty(normalizedTeam))
        {
            if (!string.IsNullOrEmpty(normalizedOpponent))
            {
                query = query.Where(m => m.IsBetween(normalizedTeam, normalizedOpponent));
            }
            else
            {
                query = query.Where(m => m.InvolvesTeam(normalizedTeam));
            }
        }

        if (!string.IsNullOrEmpty(normalizedComp))
        {
            query = query.Where(m => NormalizeCompetition(m.Competition).Equals(normalizedComp, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        if (from.HasValue)
        {
            query = query.Where(m => m.Date >= from.Value);
        }

        if (to.HasValue)
        {
            query = query.Where(m => m.Date <= to.Value);
        }

        if (!string.IsNullOrWhiteSpace(round))
        {
            query = query.Where(m => (m.Round ?? string.Empty).Equals(round, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(stage))
        {
            query = query.Where(m => (m.Stage ?? string.Empty).Equals(stage, StringComparison.OrdinalIgnoreCase));
        }

        var result = query.OrderByDescending(m => m.Date).ThenBy(m => m.MatchId).ToList();

        if (limit.HasValue && limit.Value > 0)
        {
            result = result.Take(limit.Value).ToList();
        }

        return result;
    }

    public Match? LastMatchBetween(string teamA, string teamB)
    {
        var normalizedA = NameNormalizer.Normalize(teamA);
        var normalizedB = NameNormalizer.Normalize(teamB);
        return store.Matches
            .Where(m => m.IsBetween(normalizedA, normalizedB) && m.HasResult)
            .OrderByDescending(m => m.Date)
            .FirstOrDefault();
    }

    public HeadToHead GetHeadToHead(string teamA, string teamB)
    {
        var normalizedA = NameNormalizer.Normalize(teamA);
        var normalizedB = NameNormalizer.Normalize(teamB);
        var matches = store.Matches
            .Where(m => m.IsBetween(normalizedA, normalizedB) && m.HasResult)
            .OrderByDescending(m => m.Date)
            .ToList();

        var winsA = 0;
        var winsB = 0;
        var draws = 0;
        var goalsA = 0;
        var goalsB = 0;

        foreach (var m in matches)
        {
            var aIsHome = m.NormalizedHomeTeam.Equals(normalizedA, StringComparison.OrdinalIgnoreCase);
            var aGoals = aIsHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            var bGoals = aIsHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;

            goalsA += aGoals;
            goalsB += bGoals;

            if (aGoals > bGoals) winsA++;
            else if (bGoals > aGoals) winsB++;
            else draws++;
        }

        return new HeadToHead
        {
            TeamA = teamA,
            TeamB = teamB,
            Matches = matches.Count,
            WinsA = winsA,
            WinsB = winsB,
            Draws = draws,
            GoalsA = goalsA,
            GoalsB = goalsB,
            MatchesList = matches,
        };
    }

    public TeamStatistics GetTeamStatistics(string team, int? season = null, string? competition = null, bool homeOnly = false, bool awayOnly = false)
    {
        var normalizedTeam = NameNormalizer.Normalize(team);
        var normalizedComp = string.IsNullOrWhiteSpace(competition) ? null : NormalizeCompetition(competition);

        var query = store.Matches.Where(m => m.HasResult && m.InvolvesTeam(normalizedTeam));

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        if (!string.IsNullOrEmpty(normalizedComp))
        {
            query = query.Where(m => NormalizeCompetition(m.Competition).Equals(normalizedComp, StringComparison.OrdinalIgnoreCase));
        }

        if (homeOnly)
        {
            query = query.Where(m => m.NormalizedHomeTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase));
        }
        else if (awayOnly)
        {
            query = query.Where(m => m.NormalizedAwayTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase));
        }

        var stats = ComputeTeamStats(query, team, normalizedTeam);
        stats = stats with
        {
            Context = BuildStatsContext(team, season, competition, homeOnly, awayOnly),
        };
        return stats;
    }

    public IReadOnlyList<TeamStatistics> GetLeagueStandings(int season, string? competition = null)
    {
        var normalizedComp = string.IsNullOrWhiteSpace(competition) ? null : NormalizeCompetition(competition);
        var query = store.Matches.Where(m => m.HasResult && m.Season == season);

        if (!string.IsNullOrEmpty(normalizedComp))
        {
            query = query.Where(m => NormalizeCompetition(m.Competition).Equals(normalizedComp, StringComparison.OrdinalIgnoreCase));
        }

        var teams = query
            .SelectMany(m => new[] { m.NormalizedHomeTeam, m.NormalizedAwayTeam })
            .Where(t => !string.IsNullOrEmpty(t))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        var standings = teams
            .Select(t => ComputeTeamStats(query.Where(m => m.InvolvesTeam(t)), t, t))
            .OrderByDescending(s => s.Points)
            .ThenByDescending(s => s.GoalsFor - s.GoalsAgainst)
            .ThenByDescending(s => s.GoalsFor)
            .ThenBy(s => s.Team)
            .ToList();

        return standings;
    }

    public IReadOnlyList<RelegatedTeam> GetRelegatedTeams(int season, string? competition = null)
    {
        var normalizedComp = NormalizeCompetition(competition ?? "Brasileirão");
        var standings = GetLeagueStandings(season, normalizedComp);
        if (standings.Count == 0) return Array.Empty<RelegatedTeam>();

        var count = standings.Count;
        var relegationZoneSize = count >= 20 ? 4 : count >= 10 ? count / 5 : 1;
        return standings
            .TakeLast(relegationZoneSize)
            .Select(s => new RelegatedTeam(s.Team, s.Points, s.Wins, s.Draws, s.Losses))
            .ToList();
    }

    public IReadOnlyList<Match> GetBiggestWins(string? competition = null, int? season = null, int limit = 10)
    {
        var normalizedComp = string.IsNullOrWhiteSpace(competition) ? null : NormalizeCompetition(competition);
        var query = store.Matches.Where(m => m.HasResult);

        if (!string.IsNullOrEmpty(normalizedComp))
        {
            query = query.Where(m => NormalizeCompetition(m.Competition).Equals(normalizedComp, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        return query
            .Select(m => new { Match = m, Diff = Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value) })
            .Where(x => x.Diff >= 4)
            .OrderByDescending(x => x.Diff)
            .ThenByDescending(x => x.Match.Date)
            .Take(limit)
            .Select(x => x.Match)
            .ToList();
    }

    public GlobalStatistics GetGlobalStatistics(string? competition = null, int? season = null)
    {
        var normalizedComp = string.IsNullOrWhiteSpace(competition) ? null : NormalizeCompetition(competition);
        var query = store.Matches.Where(m => m.HasResult);

        if (!string.IsNullOrEmpty(normalizedComp))
        {
            query = query.Where(m => NormalizeCompetition(m.Competition).Equals(normalizedComp, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        var matches = query.ToList();
        var total = matches.Count;
        if (total == 0) return new GlobalStatistics();

        var goals = matches.Sum(m => m.HomeGoals!.Value + m.AwayGoals!.Value);
        var homeWins = matches.Count(m => m.HomeGoals!.Value > m.AwayGoals!.Value);
        var draws = matches.Count(m => m.HomeGoals!.Value == m.AwayGoals!.Value);
        var awayWins = matches.Count(m => m.HomeGoals!.Value < m.AwayGoals!.Value);

        return new GlobalStatistics
        {
            Matches = total,
            Goals = goals,
            AverageGoalsPerMatch = (double)goals / total,
            HomeWinRate = (double)homeWins / total,
            DrawRate = (double)draws / total,
            AwayWinRate = (double)awayWins / total,
        };
    }

    public IReadOnlyList<Player> FindPlayers(string? name = null, string? nationality = null, string? club = null, string? position = null, int? minOverall = null, int limit = 50)
    {
        var query = store.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            query = query.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            query = query.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }

        if (minOverall.HasValue)
        {
            query = query.Where(p => p.Overall >= minOverall.Value);
        }

        return query
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    public IReadOnlyList<Player> GetTopPlayers(string? nationality = null, string? club = null, string? position = null, int limit = 10)
    {
        return FindPlayers(nationality: nationality, club: club, position: position, minOverall: null, limit: limit);
    }

    private static TeamStatistics ComputeTeamStats(IEnumerable<Match> matches, string displayName, string normalizedTeam)
    {
        var matchesList = matches.ToList();
        var wins = 0;
        var draws = 0;
        var losses = 0;
        var goalsFor = 0;
        var goalsAgainst = 0;
        var homeWins = 0;
        var homeDraws = 0;
        var homeLosses = 0;
        var awayWins = 0;
        var awayDraws = 0;
        var awayLosses = 0;

        foreach (var m in matchesList)
        {
            var isHome = m.NormalizedHomeTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase);
            var teamGoals = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            var oppGoals = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;

            goalsFor += teamGoals;
            goalsAgainst += oppGoals;

            if (teamGoals > oppGoals) { wins++; if (isHome) homeWins++; else awayWins++; }
            else if (teamGoals < oppGoals) { losses++; if (isHome) homeLosses++; else awayLosses++; }
            else { draws++; if (isHome) homeDraws++; else awayDraws++; }
        }

        return new TeamStatistics
        {
            Team = displayName,
            Matches = matchesList.Count,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = goalsFor,
            GoalsAgainst = goalsAgainst,
            HomeWins = homeWins,
            HomeDraws = homeDraws,
            HomeLosses = homeLosses,
            AwayWins = awayWins,
            AwayDraws = awayDraws,
            AwayLosses = awayLosses,
        };
    }

    private static string BuildStatsContext(string team, int? season, string? competition, bool homeOnly, bool awayOnly)
    {
        var sb = new StringBuilder();
        if (homeOnly) sb.Append("Home record for ");
        else if (awayOnly) sb.Append("Away record for ");
        else sb.Append("Record for ");
        sb.Append(team);
        if (season.HasValue) sb.Append($" ({season.Value})");
        if (!string.IsNullOrWhiteSpace(competition)) sb.Append($" {competition}");
        return sb.ToString();
    }

    private static string NormalizeCompetition(string? competition)
    {
        if (string.IsNullOrWhiteSpace(competition)) return string.Empty;
        var value = competition.Trim();
        if (value.Contains("Brasil", StringComparison.OrdinalIgnoreCase) || value.Contains("Serie", StringComparison.OrdinalIgnoreCase))
            return "Brasileirão";
        if (value.Contains("Libertad", StringComparison.OrdinalIgnoreCase))
            return "Copa Libertadores";
        if (value.Contains("Brasil Cup", StringComparison.OrdinalIgnoreCase) || value.Contains("Copa do Brasil", StringComparison.OrdinalIgnoreCase))
            return "Copa do Brasil";
        return value;
    }
}

public sealed record RelegatedTeam(string Team, int Points, int Wins, int Draws, int Losses);

public sealed record GlobalStatistics
{
    public int Matches { get; init; }
    public int Goals { get; init; }
    public double AverageGoalsPerMatch { get; init; }
    public double HomeWinRate { get; init; }
    public double DrawRate { get; init; }
    public double AwayWinRate { get; init; }
}
