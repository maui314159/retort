using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Services;

[McpServerToolType]
public class SoccerService
{
    private readonly List<MatchRecord> _matches;
    private readonly List<PlayerRecord> _players;

    public SoccerService(DataLoader dataLoader)
    {
        _matches = dataLoader.LoadAllMatches();
        _players = dataLoader.LoadPlayers();
    }

    [McpServerTool(Name = "search_matches")]
    public string SearchMatches(
        string? team = null,
        string? startDate = null,
        string? endDate = null,
        string? competition = null,
        string? season = null,
        int limit = 50)
    {
        var normalizedTeam = team != null ? TeamNormalizer.Normalize(team) : null;
        DateTime? start = null;
        if (startDate != null && DateTime.TryParse(startDate, out var startDateParsed)) start = startDateParsed;
        DateTime? end = null;
        if (endDate != null && DateTime.TryParse(endDate, out var endDateParsed)) end = endDateParsed;

        var results = _matches.Where(m =>
            (normalizedTeam == null || m.HomeTeam.Contains(normalizedTeam, StringComparison.OrdinalIgnoreCase) || m.AwayTeam.Contains(normalizedTeam, StringComparison.OrdinalIgnoreCase)) &&
            (start == null || (m.Date.HasValue && m.Date.Value >= start)) &&
            (end == null || (m.Date.HasValue && m.Date.Value <= end)) &&
            (competition == null || m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) &&
            (season == null || m.Season == season)
        )
        .OrderByDescending(m => m.Date)
        .Take(limit)
        .ToList();

        if (results.Count == 0)
            return "No matches found matching the criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} matches:");
        foreach (var m in results)
        {
            var dateStr = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown";
            sb.AppendLine($"- {dateStr}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition}{(m.Season != "" ? $" {m.Season}" : "")}{(m.Round != "" ? $" Round {m.Round}" : "")}{(m.Stage != "" ? $" - {m.Stage}" : "")})");
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_player_info")]
    public string GetPlayerInfo(
        string? name = null,
        string? nationality = null,
        string? club = null,
        int? minOverall = null,
        string? position = null,
        int limit = 20)
    {
        var results = _players.Where(p =>
            (name == null || p.Name.Contains(name, StringComparison.OrdinalIgnoreCase)) &&
            (nationality == null || p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase)) &&
            (club == null || p.Club.Contains(club, StringComparison.OrdinalIgnoreCase)) &&
            (minOverall == null || p.Overall >= minOverall) &&
            (position == null || p.Position.Contains(position, StringComparison.OrdinalIgnoreCase))
        )
        .OrderByDescending(p => p.Overall)
        .Take(limit)
        .ToList();

        if (results.Count == 0)
            return "No players found matching the criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} players:");
        foreach (var p in results)
        {
            sb.AppendLine($"- {p.Name} | Overall: {p.Overall} | Pos: {p.Position} | Club: {p.Club} | Nationality: {p.Nationality} | Age: {p.Age}");
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_team_statistics")]
    public string GetTeamStatistics(
        string team,
        string? competition = null,
        string? season = null)
    {
        var normalizedTeam = TeamNormalizer.Normalize(team);
        
        var teamMatches = _matches.Where(m =>
            m.HomeTeam == normalizedTeam || m.AwayTeam == normalizedTeam
        ).ToList();

        if (competition != null)
            teamMatches = teamMatches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)).ToList();
        
        if (season != null)
            teamMatches = teamMatches.Where(m => m.Season == season).ToList();

        if (teamMatches.Count == 0)
            return $"No matches found for {team} with the specified filters.";

        var stats = new TeamStatistics { TeamName = team, Competition = competition ?? "All", Season = season ?? "All" };

        foreach (var m in teamMatches)
        {
            stats.MatchesPlayed++;
            bool isHome = m.HomeTeam == normalizedTeam;
            
            if (isHome)
            {
                stats.HomeMatches++;
                stats.GoalsFor += m.HomeGoals;
                stats.GoalsAgainst += m.AwayGoals;
                if (m.HomeGoals > m.AwayGoals) { stats.Wins++; stats.HomeWins++; }
                else if (m.HomeGoals == m.AwayGoals) { stats.Draws++; stats.HomeDraws++; }
                else { stats.Losses++; stats.HomeLosses++; }
            }
            else
            {
                stats.AwayMatches++;
                stats.GoalsFor += m.AwayGoals;
                stats.GoalsAgainst += m.HomeGoals;
                if (m.AwayGoals > m.HomeGoals) { stats.Wins++; stats.AwayWins++; }
                else if (m.AwayGoals == m.HomeGoals) { stats.Draws++; stats.AwayDraws++; }
                else { stats.Losses++; stats.AwayLosses++; }
            }
        }

        var sb = new StringBuilder();
        sb.AppendLine($"{team} Statistics ({stats.Competition} {stats.Season}):");
        sb.AppendLine($"- Matches Played: {stats.MatchesPlayed} (Home: {stats.HomeMatches}, Away: {stats.AwayMatches})");
        sb.AppendLine($"- Record: {stats.Wins}W - {stats.Draws}D - {stats.Losses}L (Home: {stats.HomeWins}W-{stats.HomeDraws}D-{stats.HomeLosses}L, Away: {stats.AwayWins}W-{stats.AwayDraws}D-{stats.AwayLosses}L)");
        sb.AppendLine($"- Goals: {stats.GoalsFor} For, {stats.GoalsAgainst} Against (Diff: {stats.GoalDifference:+#;-#;0})");
        sb.AppendLine($"- Win Rate: {stats.WinRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool(Name = "get_head_to_head")]
    public string GetHeadToHead(
        string team1,
        string team2)
    {
        var norm1 = TeamNormalizer.Normalize(team1);
        var norm2 = TeamNormalizer.Normalize(team2);

        var matches = _matches.Where(m =>
            (m.HomeTeam == norm1 && m.AwayTeam == norm2) ||
            (m.HomeTeam == norm2 && m.AwayTeam == norm1)
        ).OrderByDescending(m => m.Date).ToList();

        if (matches.Count == 0)
            return $"No matches found between {team1} and {team2}.";

        int t1Wins = 0, t2Wins = 0, draws = 0, t1Goals = 0, t2Goals = 0;

        foreach (var m in matches)
        {
            bool t1IsHome = m.HomeTeam == norm1;
            int goals1 = t1IsHome ? m.HomeGoals : m.AwayGoals;
            int goals2 = t1IsHome ? m.AwayGoals : m.HomeGoals;

            t1Goals += goals1;
            t2Goals += goals2;

            if (goals1 > goals2) t1Wins++;
            else if (goals2 > goals1) t2Wins++;
            else draws++;
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-Head: {team1} vs {team2}");
        sb.AppendLine($"Total Matches: {matches.Count}");
        sb.AppendLine($"{team1} Wins: {t1Wins} | {team2} Wins: {t2Wins} | Draws: {draws}");
        sb.AppendLine($"Goals: {team1} {t1Goals} - {t2Goals} {team2}");
        sb.AppendLine("\nRecent Matches:");
        foreach (var m in matches.Take(5))
        {
            var dateStr = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown";
            sb.AppendLine($"- {dateStr}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition} {m.Season})");
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_competition_standings")]
    public string GetCompetitionStandings(
        string competition,
        string season)
    {
        var seasonMatches = _matches.Where(m => 
            m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) && m.Season == season
        ).ToList();

        if (seasonMatches.Count == 0)
            return $"No matches found for {competition} in {season}.";

        var teamStats = new Dictionary<string, CompetitionStanding>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in seasonMatches)
        {
            if (!teamStats.ContainsKey(m.HomeTeam)) teamStats[m.HomeTeam] = new CompetitionStanding { TeamName = m.HomeTeam };
            if (!teamStats.ContainsKey(m.AwayTeam)) teamStats[m.AwayTeam] = new CompetitionStanding { TeamName = m.AwayTeam };

            teamStats[m.HomeTeam].MatchesPlayed++;
            teamStats[m.AwayTeam].MatchesPlayed++;
            teamStats[m.HomeTeam].GoalsFor += m.HomeGoals;
            teamStats[m.HomeTeam].GoalsAgainst += m.AwayGoals;
            teamStats[m.AwayTeam].GoalsFor += m.AwayGoals;
            teamStats[m.AwayTeam].GoalsAgainst += m.HomeGoals;

            if (m.HomeGoals > m.AwayGoals)
            {
                teamStats[m.HomeTeam].Wins++;
                teamStats[m.AwayTeam].Losses++;
            }
            else if (m.AwayGoals > m.HomeGoals)
            {
                teamStats[m.AwayTeam].Wins++;
                teamStats[m.HomeTeam].Losses++;
            }
            else
            {
                teamStats[m.HomeTeam].Draws++;
                teamStats[m.AwayTeam].Draws++;
            }
        }

        var standings = teamStats.Values
            .OrderByDescending(s => s.Points)
            .ThenByDescending(s => s.GoalDifference)
            .ThenByDescending(s => s.GoalsFor)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} Standings (Calculated):");
        sb.AppendLine($"{"Pos",-4} {"Team",-25} {"P",-3} {"W",-3} {"D",-3} {"L",-3} {"GF",-3} {"GA",-3} {"GD",-4} {"Pts"}");
        sb.AppendLine(new string('-', 60));
        
        for (int i = 0; i < Math.Min(20, standings.Count); i++)
        {
            var s = standings[i];
            sb.AppendLine($"{i + 1,-4} {s.TeamName,-25} {s.MatchesPlayed,-3} {s.Wins,-3} {s.Draws,-3} {s.Losses,-3} {s.GoalsFor,-3} {s.GoalsAgainst,-3} {s.GoalDifference,-4} {s.Points}");
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_statistical_analysis")]
    public string GetStatisticalAnalysis(
        string? competition = null,
        string? season = null)
    {
        var matches = _matches.Where(m =>
            (competition == null || m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) &&
            (season == null || m.Season == season)
        ).ToList();

        if (matches.Count == 0)
            return "No matches found for the specified criteria.";

        int totalGoals = matches.Sum(m => m.HomeGoals + m.AwayGoals);
        double avgGoals = (double)totalGoals / matches.Count;
        int homeWins = matches.Count(m => m.HomeGoals > m.AwayGoals);
        double homeWinRate = (double)homeWins / matches.Count * 100;

        var biggestWins = matches
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .ThenByDescending(m => Math.Max(m.HomeGoals, m.AwayGoals))
            .Take(5)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Statistical Analysis ({competition ?? "All Competitions"}{(season != null ? $" {season}" : "")}):");
        sb.AppendLine($"- Total Matches: {matches.Count}");
        sb.AppendLine($"- Total Goals: {totalGoals}");
        sb.AppendLine($"- Average Goals per Match: {avgGoals:F2}");
        sb.AppendLine($"- Home Win Rate: {homeWinRate:F1}%");

        sb.AppendLine("\nBiggest Victories:");
        foreach (var m in biggestWins)
        {
            var dateStr = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown";
            sb.AppendLine($"- {dateStr}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition} {m.Season})");
        }

        return sb.ToString();
    }
}
