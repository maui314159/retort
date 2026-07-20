using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

public class SoccerDataService
{
    private readonly List<UnifiedMatch> _matches;
    private readonly List<FifaPlayer> _players;

    public SoccerDataService(IEnumerable<UnifiedMatch> matches, IEnumerable<FifaPlayer> players)
    {
        _matches = matches.ToList();
        _players = players.ToList();
    }

    public static SoccerDataService LoadFromDisk(string kaggleDataPath)
    {
        var loader = new CsvDataLoader(kaggleDataPath);
        return new SoccerDataService(loader.LoadAllMatches(), loader.LoadPlayers());
    }

    public List<UnifiedMatch> FindMatches(
        string? team1 = null,
        string? team2 = null,
        int? season = null,
        string? competition = null,
        int limit = 100)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team1))
        {
            query = query.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, team1) ||
                TeamNameNormalizer.Matches(m.AwayTeam, team1));
        }

        if (!string.IsNullOrWhiteSpace(team2))
        {
            query = query.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, team2) ||
                TeamNameNormalizer.Matches(m.AwayTeam, team2));
        }

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var comp = competition.ToLowerInvariant();
            query = query.Where(m => m.Competition.ToLowerInvariant().Contains(comp));
        }

        return query
            .OrderByDescending(m => m.DateTime ?? DateTime.MinValue)
            .Take(limit)
            .ToList();
    }

    public TeamStats GetTeamStats(string teamName, int? season = null, string? competition = null)
    {
        var matches = FindMatches(teamName, season: season, competition: competition, limit: int.MaxValue);

        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, teamName);
            var teamGoals = isHome ? m.HomeGoal : m.AwayGoal;
            var oppGoals = isHome ? m.AwayGoal : m.HomeGoal;

            goalsFor += teamGoals;
            goalsAgainst += oppGoals;

            if (teamGoals > oppGoals) wins++;
            else if (teamGoals == oppGoals) draws++;
            else losses++;
        }

        return new TeamStats(teamName, matches.Count, wins, draws, losses, goalsFor, goalsAgainst);
    }

    public HeadToHeadStats GetHeadToHead(string team1, string team2)
    {
        var matches = FindMatches(team1, team2, limit: int.MaxValue);

        int team1Wins = 0, team2Wins = 0, draws = 0;
        int team1Goals = 0, team2Goals = 0;

        foreach (var m in matches)
        {
            bool team1IsHome = TeamNameNormalizer.Matches(m.HomeTeam, team1);
            var t1Goals = team1IsHome ? m.HomeGoal : m.AwayGoal;
            var t2Goals = team1IsHome ? m.AwayGoal : m.HomeGoal;

            team1Goals += t1Goals;
            team2Goals += t2Goals;

            if (t1Goals > t2Goals) team1Wins++;
            else if (t2Goals > t1Goals) team2Wins++;
            else draws++;
        }

        return new HeadToHeadStats(team1, team2, matches.Count, team1Wins, draws, team2Wins, team1Goals, team2Goals, matches);
    }

    public List<StandingsEntry> GetBrasileiraStandings(int season)
    {
        var matches = _matches
            .Where(m => m.Season == season &&
                        (m.Competition.Contains("Brasileirao", StringComparison.OrdinalIgnoreCase) ||
                         m.Competition.Contains("Brasileiro", StringComparison.OrdinalIgnoreCase)))
            .ToList();

        var table = new Dictionary<string, StandingsEntry>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            var home = TeamNameNormalizer.Normalize(m.HomeTeam);
            var away = TeamNameNormalizer.Normalize(m.AwayTeam);

            if (!table.ContainsKey(home)) table[home] = new StandingsEntry(home);
            if (!table.ContainsKey(away)) table[away] = new StandingsEntry(away);

            table[home] = table[home].AddMatch(m.HomeGoal, m.AwayGoal);
            table[away] = table[away].AddMatch(m.AwayGoal, m.HomeGoal);
        }

        return table.Values
            .OrderByDescending(e => e.Points)
            .ThenByDescending(e => e.GoalDifference)
            .ThenByDescending(e => e.GoalsFor)
            .ToList();
    }

    public List<FifaPlayer> FindPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minRating = null,
        int limit = 50)
    {
        var query = _players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(nationality))
            query = query.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(club))
            query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));

        if (minRating.HasValue)
            query = query.Where(p => p.Overall >= minRating.Value);

        return query
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    public List<UnifiedMatch> GetBiggestWins(string? competition = null, int limit = 20)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var comp = competition.ToLowerInvariant();
            query = query.Where(m => m.Competition.ToLowerInvariant().Contains(comp));
        }

        return query
            .OrderByDescending(m => Math.Abs(m.HomeGoal - m.AwayGoal))
            .Take(limit)
            .ToList();
    }

    public GlobalStats GetGlobalStats(string? competition = null)
    {
        var matches = string.IsNullOrWhiteSpace(competition)
            ? _matches
            : _matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)).ToList();

        if (matches.Count == 0)
            return new GlobalStats(0, 0, 0, 0, 0);

        var totalGoals = matches.Sum(m => m.HomeGoal + m.AwayGoal);
        var homeWins = matches.Count(m => m.HomeGoal > m.AwayGoal);
        var draws = matches.Count(m => m.HomeGoal == m.AwayGoal);
        var awayWins = matches.Count(m => m.AwayGoal > m.HomeGoal);
        var avgGoals = (double)totalGoals / matches.Count;

        return new GlobalStats(matches.Count, avgGoals, homeWins, draws, awayWins);
    }
}

public record TeamStats(
    string TeamName,
    int Played,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst)
{
    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Played == 0 ? 0 : (double)Wins / Played * 100;
}

public record HeadToHeadStats(
    string Team1,
    string Team2,
    int TotalMatches,
    int Team1Wins,
    int Draws,
    int Team2Wins,
    int Team1Goals,
    int Team2Goals,
    List<UnifiedMatch> Matches);

public record StandingsEntry(string Team)
{
    public int Played { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;

    public StandingsEntry AddMatch(int goalsFor, int goalsAgainst) => this with
    {
        Played = Played + 1,
        Wins = goalsFor > goalsAgainst ? Wins + 1 : Wins,
        Draws = goalsFor == goalsAgainst ? Draws + 1 : Draws,
        Losses = goalsFor < goalsAgainst ? Losses + 1 : Losses,
        GoalsFor = GoalsFor + goalsFor,
        GoalsAgainst = GoalsAgainst + goalsAgainst,
    };
}

public record GlobalStats(
    int TotalMatches,
    double AvgGoalsPerMatch,
    int HomeWins,
    int Draws,
    int AwayWins)
{
    public double HomeWinRate => TotalMatches == 0 ? 0 : (double)HomeWins / TotalMatches * 100;
    public double DrawRate => TotalMatches == 0 ? 0 : (double)Draws / TotalMatches * 100;
    public double AwayWinRate => TotalMatches == 0 ? 0 : (double)AwayWins / TotalMatches * 100;
}
