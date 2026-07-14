// <copyright file="SoccerMcpTools.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - MCP tool handlers exposed by the server.
//
// Tools follow the Model Context Protocol (MCP) and return plain text intended to be
// consumed directly by a connected LLM. They intentionally avoid complex nested JSON
// so that answers are readable and can be streamed inline.
// </copyright>
using System.ComponentModel;
using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;
using BrazilianSoccerMcp.Core.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server.Tools;

/// <summary>
/// Exposes Brazilian soccer queries as MCP tools.
/// </summary>
[McpServerToolType]
public sealed class SoccerMcpTools
{
    private readonly SoccerQueryService _queryService;

    public SoccerMcpTools(SoccerQueryService queryService)
    {
        _queryService = queryService ?? throw new ArgumentNullException(nameof(queryService));
    }

    [McpServerTool, Description("Search for soccer matches by team, date range, competition, season or round.")]
    public string SearchMatches(
        [Description("Team name to search for (home, away or either).")] string? team = null,
        [Description("Optional opponent to narrow the search.")] string? opponent = null,
        [Description("Start date (yyyy-MM-dd).")] string? startDate = null,
        [Description("End date (yyyy-MM-dd).")] string? endDate = null,
        [Description("Competition filter: Brasileirão, Copa do Brasil, Copa Libertadores.")] string? competition = null,
        [Description("Season year.")] int? season = null,
        [Description("Round or stage substring.")] string? round = null,
        [Description("Maximum number of results.")] int limit = 20)
    {
        var criteria = new MatchSearchCriteria
        {
            Team = team,
            Opponent = opponent,
            StartDate = ParseDate(startDate),
            EndDate = ParseDate(endDate),
            Competition = competition,
            Season = season,
            Round = round,
            Limit = limit,
            SortBy = "date_desc"
        };

        var matches = _queryService.SearchMatches(criteria);
        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        var lines = matches.Select(m =>
            $"- {m.Date:yyyy-MM-dd}: {m.ResultText} ({m.Competition}{(m.Season.HasValue ? " " + m.Season : "")}{(m.Round != null ? " Round " + m.Round : "")})");

        return $"Found {matches.Count} matches:\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("Get head-to-head matches and statistics between two teams.")]
    public string GetHeadToHead(
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Optional season year filter.")] int? season = null)
    {
        var matches = _queryService.GetHeadToHead(teamA, teamB, season);
        var (aWins, draws, bWins) = _queryService.GetHeadToHeadStats(teamA, teamB);

        if (matches.Count == 0)
            return $"No matches found between {teamA} and {teamB}.";

        var lines = matches.Take(20).Select(m =>
            $"- {m.Date:yyyy-MM-dd}: {m.ResultText} ({m.Competition}{(m.Season.HasValue ? " " + m.Season : "")})");

        return $"{teamA} vs {teamB} ({matches.Count} matches in dataset):\n"
            + string.Join("\n", lines)
            + $"\n\nHead-to-head: {teamA} {aWins} wins, {teamB} {bWins} wins, {draws} draws";
    }

    [McpServerTool, Description("Get overall or season-specific team statistics (wins, draws, losses, goals).")]
    public string GetTeamStatistics(
        [Description("Team name.")] string team,
        [Description("Optional season year filter.")] int? season = null,
        [Description("Optional competition filter.")] string? competition = null)
    {
        var stats = _queryService.GetTeamStatistics(team, season, competition);

        return $"{team}{(season.HasValue ? " " + season : "")}{(competition != null ? " " + competition : "")} statistics:\n"
            + $"- Matches: {stats.Matches}\n"
            + $"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}\n"
            + $"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}\n"
            + $"- Win rate: {stats.WinRate:F1}%";
    }

    [McpServerTool, Description("Get home vs away split statistics for a team.")]
    public string GetHomeAwayStatistics(
        [Description("Team name.")] string team,
        [Description("Optional season year filter.")] int? season = null,
        [Description("Optional competition filter.")] string? competition = null)
    {
        var v = _queryService.GetTeamVenueStatistics(team, season, competition);

        return $"{team} home/away record:\n"
            + $"Home - Matches: {v.Home.Matches}, Wins: {v.Home.Wins}, Draws: {v.Home.Draws}, Losses: {v.Home.Losses}, "
            + $"GF: {v.Home.GoalsFor}, GA: {v.Home.GoalsAgainst}, Win rate: {v.Home.WinRate:F1}%\n"
            + $"Away - Matches: {v.Away.Matches}, Wins: {v.Away.Wins}, Draws: {v.Away.Draws}, Losses: {v.Away.Losses}, "
            + $"GF: {v.Away.GoalsFor}, GA: {v.Away.GoalsAgainst}, Win rate: {v.Away.WinRate:F1}%\n"
            + $"Overall - Matches: {v.Overall.Matches}, Wins: {v.Overall.Wins}, Win rate: {v.Overall.WinRate:F1}%";
    }

    [McpServerTool, Description("Search players by name, nationality, club, position or rating.")]
    public string SearchPlayers(
        [Description("Substring match against player name.")] string? name = null,
        [Description("Nationality filter, e.g. Brazil.")] string? nationality = null,
        [Description("Club name filter.")] string? club = null,
        [Description("Position filter, e.g. ST, GK, LW.")] string? position = null,
        [Description("Minimum overall rating.")] int? minOverall = null,
        [Description("Maximum number of results.")] int limit = 10)
    {
        var criteria = new PlayerSearchCriteria
        {
            Name = name,
            Nationality = nationality,
            Club = club,
            Position = position,
            MinOverall = minOverall,
            Limit = limit,
            SortBy = "overall_desc"
        };

        var players = _queryService.SearchPlayers(criteria);
        if (players.Count == 0)
            return "No players found for the given criteria.";

        var lines = players.Select(p =>
            $"- {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}, Nationality: {p.Nationality}");

        return $"Found {players.Count} players:\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("Get competition standings/table for a season.")]
    public string GetStandings(
        [Description("Competition name: Brasileirão, Copa do Brasil, Copa Libertadores.")] string competition,
        [Description("Season year.")] int season,
        [Description("Maximum rows to include (default 20).")] int limit = 20)
    {
        var table = _queryService.GetStandings(competition, season);
        if (table.Count == 0)
            return $"No standings available for {competition} {season}.";

        var lines = table.Take(limit).Select((s, i) =>
            $"{i + 1}. {s.Team} - {s.Points} pts ({s.Wins}W, {s.Draws}D, {s.Losses}L), GD: {s.GoalDifference:+0;-0;0}");

        return $"{season} {competition} standings:\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("Get the biggest wins in the dataset.")]
    public string GetBiggestWins(
        [Description("Optional competition filter.")] string? competition = null,
        [Description("Optional season year filter.")] int? season = null,
        [Description("Maximum number of results.")] int limit = 10)
    {
        var wins = _queryService.GetBiggestWins(competition, limit, season);
        if (wins.Count == 0)
            return "No big wins found for the given criteria.";

        var lines = wins.Select(m =>
            $"- {m.Date:yyyy-MM-dd}: {m.ResultText} ({m.Competition}{(m.Season.HasValue ? " " + m.Season : "")})");

        return "Biggest victories (by goal difference):\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("Get aggregate competition statistics such as average goals and home win rate.")]
    public string GetCompetitionStatistics(
        [Description("Optional competition filter.")] string? competition = null,
        [Description("Optional season year filter.")] int? season = null)
    {
        var stats = _queryService.GetCompetitionStatistics(competition, season);

        return $"Competition statistics{(competition != null ? " - " + competition : "")}:\n"
            + $"- Matches: {stats.MatchesPlayed}\n"
            + $"- Average goals per match: {stats.AverageGoalsPerMatch:F2}\n"
            + $"- Home wins: {stats.HomeWins} ({stats.HomeWinRate:F1}%)\n"
            + $"- Draws: {stats.Draws} ({stats.DrawRate:F1}%)\n"
            + $"- Away wins: {stats.AwayWins} ({stats.AwayWinRate:F1}%)";
    }

    [McpServerTool, Description("Get teams with the best away records.")]
    public string GetBestAwayRecords(
        [Description("Optional season year filter.")] int? season = null,
        [Description("Minimum number of away matches to be considered.")] int minMatches = 10,
        [Description("Maximum number of results.")] int limit = 10)
    {
        var records = _queryService.GetBestAwayRecords(season, null, minMatches);
        if (records.Count == 0)
            return "No teams meet the minimum away match threshold.";

        var lines = records.Take(limit).Select((r, i) =>
            $"{i + 1}. {r.Team} - {r.WinRate:F1}% ({r.Wins}W/{r.Draws}D/{r.Losses}L)");

        return "Best away records:\n" + string.Join("\n", lines);
    }

    private static DateTime? ParseDate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;

        if (DateTime.TryParseExact(value, "yyyy-MM-dd", CultureInfo.InvariantCulture,
            DateTimeStyles.None, out var dt))
            return dt;

        if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return dt;

        return null;
    }
}
