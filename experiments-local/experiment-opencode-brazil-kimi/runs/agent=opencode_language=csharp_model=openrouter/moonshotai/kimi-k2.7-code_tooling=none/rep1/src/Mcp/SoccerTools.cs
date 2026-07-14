/*
 * Brazilian Soccer MCP Server - MCP Tools
 *
 * Exposes the query capabilities as MCP tools. Each tool maps a natural
 * language question category to the query engine and returns formatted text.
 */
using BrazilianSoccerMcp.Queries;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Mcp;

[McpServerToolType]
public sealed class SoccerTools
{
    private readonly QueryEngine _engine;

    public SoccerTools(QueryEngine engine)
    {
        _engine = engine;
    }

    [McpServerTool(Name = "find_matches", Title = "Find matches by team, opponent, season, competition or date range.")]
    public string FindMatches(
        string? team = null,
        string? opponent = null,
        int? season = null,
        string? competition = null,
        string? dateFrom = null,
        string? dateTo = null,
        int limit = 20)
    {
        DateTime? from = string.IsNullOrWhiteSpace(dateFrom) ? null : DateTime.Parse(dateFrom);
        DateTime? to = string.IsNullOrWhiteSpace(dateTo) ? null : DateTime.Parse(dateTo);
        var matches = _engine.FindMatches(team, opponent, season, competition, from, to).Take(limit);
        var title = $"Matches{(string.IsNullOrWhiteSpace(team) ? "" : $" for {team}")}"
            + $"{(string.IsNullOrWhiteSpace(opponent) ? "" : $" vs {opponent}")}"
            + $"{(season.HasValue ? $" in {season}" : "")}"
            + $"{(string.IsNullOrWhiteSpace(competition) ? "" : $" ({competition})")}";
        return ResponseFormatter.FormatMatches(title, matches);
    }

    [McpServerTool(Name = "get_team_statistics", Title = "Get win/loss/draw and goal statistics for a team.")]
    public string GetTeamStatistics(
        string team,
        int? season = null,
        string? competition = null,
        bool homeOnly = false,
        bool awayOnly = false)
    {
        var stats = _engine.GetTeamStatistics(team, season, competition, homeOnly, awayOnly);
        return ResponseFormatter.FormatTeamStatistics(stats);
    }

    [McpServerTool(Name = "get_head_to_head", Title = "Get head-to-head statistics between two teams.")]
    public string GetHeadToHead(string teamA, string teamB)
    {
        return ResponseFormatter.FormatHeadToHead(_engine.GetHeadToHead(teamA, teamB));
    }

    [McpServerTool(Name = "search_players", Title = "Search players by name, nationality, club, position or overall rating range.")]
    public string SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? maxOverall = null,
        int limit = 20)
    {
        var players = _engine.SearchPlayers(name, nationality, club, position, minOverall, maxOverall).Take(limit);
        return ResponseFormatter.FormatPlayers("Players", players);
    }

    [McpServerTool(Name = "get_top_players", Title = "Get top players by overall rating, optionally filtered by nationality, club or position.")]
    public string GetTopPlayers(
        string? nationality = null,
        string? club = null,
        string? position = null,
        int count = 10)
    {
        return ResponseFormatter.FormatPlayers(
            $"Top players{(string.IsNullOrWhiteSpace(nationality) ? "" : $" from {nationality}")}",
            _engine.GetTopPlayers(nationality, club, position, count));
    }

    [McpServerTool(Name = "get_competition_standings", Title = "Calculate league standings for a season and competition.")]
    public string GetCompetitionStandings(int season, string competition)
    {
        return ResponseFormatter.FormatStandings(season, competition, _engine.GetCompetitionStandings(season, competition));
    }

    [McpServerTool(Name = "get_team_competitions", Title = "List all competitions a team has played in.")]
    public string GetTeamCompetitions(string team)
    {
        var competitions = _engine.GetTeamCompetitions(team);
        return competitions.Count == 0
            ? $"No competitions found for {team}."
            : $"{team} has played in:\n" + string.Join("\n", competitions.Select(c => $"- {c}"));
    }

    [McpServerTool(Name = "get_biggest_wins", Title = "Get the biggest wins by goal difference.")]
    public string GetBiggestWins(string? competition = null, int count = 10)
    {
        return ResponseFormatter.FormatBiggestWins(_engine.GetBiggestWins(competition, count));
    }

    [McpServerTool(Name = "get_average_goals", Title = "Calculate the average goals per match.")]
    public string GetAverageGoals(string? competition = null)
    {
        return ResponseFormatter.FormatAverageGoals(_engine.GetAverageGoalsPerMatch(competition), competition);
    }

    [McpServerTool(Name = "get_best_away_record", Title = "Find the team with the best away record.")]
    public string GetBestAwayRecord(string? competition = null, int? season = null)
    {
        return ResponseFormatter.FormatTeamStatistics(_engine.GetBestAwayRecord(competition, season));
    }
}
