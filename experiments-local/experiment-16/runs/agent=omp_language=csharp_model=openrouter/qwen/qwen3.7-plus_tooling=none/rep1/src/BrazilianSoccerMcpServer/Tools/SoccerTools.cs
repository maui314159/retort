using System.Text;
using BrazilianSoccerMcpServer.Models;
using BrazilianSoccerMcpServer.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcpServer.Tools;

[McpServerToolType]
public class SoccerTools
{
    private readonly BrazilianSoccerDataStore _dataStore;

    public SoccerTools(BrazilianSoccerDataStore dataStore)
    {
        _dataStore = dataStore;
    }

    [McpServerTool]
    public string SearchMatches(
        string? homeTeam = null,
        string? awayTeam = null,
        string? eitherTeam = null,
        string? competition = null,
        int? season = null,
        string? startDate = null,
        string? endDate = null,
        int limit = 50)
    {
        var query = _dataStore.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(homeTeam))
        {
            var normalized = TeamNameNormalizer.Normalize(homeTeam);
            query = query.Where(m => TeamNameNormalizer.Matches(m.HomeTeam, normalized));
        }

        if (!string.IsNullOrWhiteSpace(awayTeam))
        {
            var normalized = TeamNameNormalizer.Normalize(awayTeam);
            query = query.Where(m => TeamNameNormalizer.Matches(m.AwayTeam, normalized));
        }

        if (!string.IsNullOrWhiteSpace(eitherTeam))
        {
            var normalized = TeamNameNormalizer.Normalize(eitherTeam);
            query = query.Where(m => TeamNameNormalizer.Matches(m.HomeTeam, normalized) || TeamNameNormalizer.Matches(m.AwayTeam, normalized));
        }

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var compLower = competition.ToLowerInvariant();
            query = query.Where(m => m.Competition.ToLowerInvariant().Contains(compLower));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        if (!string.IsNullOrWhiteSpace(startDate) && DateTime.TryParse(startDate, out var start))
        {
            query = query.Where(m => m.Date >= start);
        }

        if (!string.IsNullOrWhiteSpace(endDate) && DateTime.TryParse(endDate, out var end))
        {
            query = query.Where(m => m.Date <= end);
        }

        var results = query.OrderByDescending(m => m.Date).Take(limit).ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} matches.");
        foreach (var m in results)
        {
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition}, Season {m.Season}{(string.IsNullOrWhiteSpace(m.Round) ? "" : $", {m.Round}")})");
        }

        return sb.ToString();
    }

    [McpServerTool]
    public string GetTeamStats(
        string teamName,
        int? season = null,
        string? competition = null)
    {
        var normalized = TeamNameNormalizer.Normalize(teamName);
        var query = _dataStore.Matches.Where(m => 
            TeamNameNormalizer.Matches(m.HomeTeam, normalized) || TeamNameNormalizer.Matches(m.AwayTeam, normalized));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var compLower = competition.ToLowerInvariant();
            query = query.Where(m => m.Competition.ToLowerInvariant().Contains(compLower));
        }

        var matches = query.ToList();
        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, normalized);
            var teamGoals = isHome ? m.HomeGoal : m.AwayGoal;
            var oppGoals = isHome ? m.AwayGoal : m.HomeGoal;

            goalsFor += teamGoals;
            goalsAgainst += oppGoals;

            if (teamGoals > oppGoals) wins++;
            else if (teamGoals == oppGoals) draws++;
            else losses++;
        }

        var total = matches.Count;
        var winRate = total > 0 ? (double)wins / total * 100 : 0;

        return $"""
        Statistics for {teamName}:
        - Matches: {total}
        - Wins: {wins}, Draws: {draws}, Losses: {losses}
        - Goals For: {goalsFor}, Goals Against: {goalsAgainst}
        - Win Rate: {winRate:F1}%
        """;
    }

    [McpServerTool]
    public string GetHeadToHead(string team1, string team2)
    {
        var norm1 = TeamNameNormalizer.Normalize(team1);
        var norm2 = TeamNameNormalizer.Normalize(team2);

        var matches = _dataStore.Matches.Where(m =>
            (TeamNameNormalizer.Matches(m.HomeTeam, norm1) && TeamNameNormalizer.Matches(m.AwayTeam, norm2)) ||
            (TeamNameNormalizer.Matches(m.HomeTeam, norm2) && TeamNameNormalizer.Matches(m.AwayTeam, norm1))
        ).OrderByDescending(m => m.Date).ToList();

        int t1Wins = 0, t2Wins = 0, draws = 0;
        int t1Goals = 0, t2Goals = 0;

        foreach (var m in matches)
        {
            bool t1IsHome = TeamNameNormalizer.Matches(m.HomeTeam, norm1);
            var goals1 = t1IsHome ? m.HomeGoal : m.AwayGoal;
            var goals2 = t1IsHome ? m.AwayGoal : m.HomeGoal;

            t1Goals += goals1;
            t2Goals += goals2;

            if (goals1 > goals2) t1Wins++;
            else if (goals1 < goals2) t2Wins++;
            else draws++;
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-Head: {team1} vs {team2}");
        sb.AppendLine($"Total Matches: {matches.Count}");
        sb.AppendLine($"{team1} Wins: {t1Wins}, {team2} Wins: {t2Wins}, Draws: {draws}");
        sb.AppendLine($"Goals: {team1} {t1Goals} - {t2Goals} {team2}");
        sb.AppendLine("Recent Matches:");
        foreach (var m in matches.Take(5))
        {
            sb.AppendLine($"- {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})");
        }

        return sb.ToString();
    }

    [McpServerTool]
    public string SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        int? minOverall = null,
        int limit = 20)
    {
        var query = _dataStore.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            var nameLower = name.ToLowerInvariant();
            query = query.Where(p => p.Name.ToLowerInvariant().Contains(nameLower));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var natLower = nationality.ToLowerInvariant();
            query = query.Where(p => p.Nationality.ToLowerInvariant().Contains(natLower));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            var normClub = TeamNameNormalizer.Normalize(club);
            query = query.Where(p => TeamNameNormalizer.Matches(p.Club, normClub));
        }

        if (minOverall.HasValue)
        {
            query = query.Where(p => p.Overall >= minOverall.Value);
        }

        var results = query.OrderByDescending(p => p.Overall).ThenBy(p => p.Name).Take(limit).ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} players.");
        foreach (var p in results)
        {
            sb.AppendLine($"- {p.Name} (Age: {p.Age}, Nationality: {p.Nationality})");
            sb.AppendLine($"  Club: {p.Club}, Position: {p.Position}, Overall: {p.Overall}, Potential: {p.Potential}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    public string GetCompetitionStandings(
        string competition,
        int season)
    {
        var compLower = TeamNameNormalizer.RemoveAccents(competition);
        var matches = _dataStore.Matches.Where(m => 
            m.Season == season && TeamNameNormalizer.RemoveAccents(m.Competition).Contains(compLower)
        ).ToList();

        if (matches.Count == 0)
            return $"No matches found for {competition} in season {season}.";

        var standings = new Dictionary<string, (int Played, int Won, int Drawn, int Lost, int GoalsFor, int GoalsAgainst, int Points)>();

        foreach (var m in matches)
        {
            if (!standings.ContainsKey(m.HomeTeam))
                standings[m.HomeTeam] = (0, 0, 0, 0, 0, 0, 0);
            if (!standings.ContainsKey(m.AwayTeam))
                standings[m.AwayTeam] = (0, 0, 0, 0, 0, 0, 0);

            var home = standings[m.HomeTeam];
            var away = standings[m.AwayTeam];

            home = home with { Played = home.Played + 1, GoalsFor = home.GoalsFor + m.HomeGoal, GoalsAgainst = home.GoalsAgainst + m.AwayGoal };
            away = away with { Played = away.Played + 1, GoalsFor = away.GoalsFor + m.AwayGoal, GoalsAgainst = away.GoalsAgainst + m.HomeGoal };

            if (m.HomeGoal > m.AwayGoal)
            {
                home = home with { Won = home.Won + 1, Points = home.Points + 3 };
                away = away with { Lost = away.Lost + 1 };
            }
            else if (m.HomeGoal < m.AwayGoal)
            {
                away = away with { Won = away.Won + 1, Points = away.Points + 3 };
                home = home with { Lost = home.Lost + 1 };
            }
            else
            {
                home = home with { Drawn = home.Drawn + 1, Points = home.Points + 1 };
                away = away with { Drawn = away.Drawn + 1, Points = away.Points + 1 };
            }

            standings[m.HomeTeam] = home;
            standings[m.AwayTeam] = away;
        }

        var sorted = standings.OrderByDescending(x => x.Value.Points)
                              .ThenByDescending(x => x.Value.GoalsFor - x.Value.GoalsAgainst)
                              .ThenByDescending(x => x.Value.GoalsFor)
                              .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"{season} {competition} Standings (Calculated):");
        int rank = 1;
        foreach (var (team, stats) in sorted.Take(20))
        {
            sb.AppendLine($"{rank}. {team} - {stats.Points} pts ({stats.Won}W, {stats.Drawn}D, {stats.Lost}L) GF:{stats.GoalsFor} GA:{stats.GoalsAgainst}");
            rank++;
        }

        return sb.ToString();
    }

    [McpServerTool]
    public string GetStatisticalAnalysis(
        string? competition = null,
        int? season = null)
    {
        var query = _dataStore.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var compLower = TeamNameNormalizer.RemoveAccents(competition);
            query = query.Where(m => TeamNameNormalizer.RemoveAccents(m.Competition).Contains(compLower));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        var matches = query.ToList();
        if (matches.Count == 0)
            return "No matches found for the specified criteria.";

        var totalGoals = matches.Sum(m => m.HomeGoal + m.AwayGoal);
        var avgGoals = (double)totalGoals / matches.Count;
        var homeWins = matches.Count(m => m.HomeGoal > m.AwayGoal);
        var homeWinRate = (double)homeWins / matches.Count * 100;

        var biggestWins = matches
            .Select(m => new { m.Date, m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Competition, Diff = Math.Abs(m.HomeGoal - m.AwayGoal) })
            .OrderByDescending(x => x.Diff)
            .ThenByDescending(x => Math.Max(x.HomeGoal, x.AwayGoal))
            .Take(5)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Statistical Analysis ({matches.Count} matches):");
        sb.AppendLine($"- Average goals per match: {avgGoals:F2}");
        sb.AppendLine($"- Home win rate: {homeWinRate:F1}%");
        sb.AppendLine("Biggest victories:");
        foreach (var w in biggestWins)
        {
            sb.AppendLine($"- {w.Date:yyyy-MM-dd}: {w.HomeTeam} {w.HomeGoal}-{w.AwayGoal} {w.AwayTeam} ({w.Competition})");
        }

        return sb.ToString();
    }
}
