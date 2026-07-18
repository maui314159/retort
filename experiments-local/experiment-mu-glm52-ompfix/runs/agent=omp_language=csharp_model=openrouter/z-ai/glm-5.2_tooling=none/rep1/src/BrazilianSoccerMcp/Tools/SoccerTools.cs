// Brazilian Soccer MCP Server - Player, Competition & Stats MCP tools
//
// Context: Companion tool set to MatchTools. These tools answer the spec's
// player queries (search/rate/filter by nationality & club), competition
// queries (standings/champion), and statistical analysis (biggest wins, goals
// per match, best records). All injected with the same SoccerDataService.

using System.ComponentModel;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>MCP tools for querying players, competitions, and aggregate statistics.</summary>
[McpServerToolType]
public sealed class SoccerTools
{
    private readonly SoccerDataService _data;
    public SoccerTools(SoccerDataService data) => _data = data;

    [McpServerTool, Description("Search FIFA player database by name, nationality, club, or position. Results sorted by overall rating descending.")]
    public string SearchPlayers(
        [Description("Player name to search for (partial match). Optional.")] string? name = null,
        [Description("Nationality filter, e.g. 'Brazil'. Optional.")] string? nationality = null,
        [Description("Club name filter (partial match), e.g. 'Flamengo'. Optional.")] string? club = null,
        [Description("Position filter, e.g. 'ST', 'GK', 'LW'. Optional.")] string? position = null,
        [Description("Minimum overall rating. Optional.")] int? minOverall = null,
        [Description("Maximum number of players to return. Default 10.")] int limit = 10)
    {
        _data.EnsureLoaded();
        IEnumerable<Player> query = _data.Players;

        if (!string.IsNullOrWhiteSpace(name))
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(nationality))
            query = query.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(club))
            query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p => p.Position != null && p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        if (minOverall.HasValue)
            query = query.Where(p => p.Overall >= minOverall);

        var results = query.OrderByDescending(p => p.Overall ?? 0).Take(Math.Max(1, limit)).ToList();
        if (results.Count == 0)
            return "No players found matching the criteria.";

        var total = query.Count();
        var lines = results.Select((p, i) => $"{i + 1}. {p.Summary}");
        return $"Players ({results.Count} shown of {total}):\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("List all players at a given club, sorted by overall rating.")]
    public string GetClubPlayers(
        [Description("Club name, e.g. 'Flamengo', 'Palmeiras'.")] string club,
        [Description("Maximum number of players. Default 20.")] int limit = 20)
    {
        _data.EnsureLoaded();
        var players = _data.Players
            .Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .Take(Math.Max(1, limit))
            .ToList();

        if (players.Count == 0)
            return $"No players found at club '{club}'.";

        var lines = players.Select((p, i) => $"{i + 1}. {p.Summary}");
        var avg = players.Average(p => p.Overall ?? 0);
        return $"Players at {club} ({players.Count}, avg rating {avg:F1}):\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("Compute the league standings for a competition season (calculated from match results). Competition must include 'Brasileirão' for historical Serie A data.")]
    public string GetStandings(
        [Description("Competition name, e.g. 'Brasileirão', 'Copa do Brasil'.")] string competition,
        [Description("Season year, e.g. 2019.")] int season)
    {
        _data.EnsureLoaded();
        var standings = _data.Standings(competition, season);
        if (standings.Count == 0)
            return $"No standings data found for {competition} {season}.";

        var lines = standings.Take(20).Select(s =>
            $"{s.Position}. {s.Team} - {s.Points} pts ({s.Wins}W, {s.Draws}D, {s.Losses}L)" +
            (s.Champion ? " - Champion" : ""));
        return $"{season} {competition} Standings ({standings.Count} teams):\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("Find the champion (top team by points) for a competition season.")]
    public string GetChampion(
        [Description("Competition name, e.g. 'Brasileirão'.")] string competition,
        [Description("Season year, e.g. 2019.")] int season)
    {
        _data.EnsureLoaded();
        var standings = _data.Standings(competition, season);
        if (standings.Count == 0)
            return $"No standings data found for {competition} {season}.";

        var champ = standings[0];
        return $"{season} {competition} Champion: {champ.Team} - {champ.Points} pts ({champ.Wins}W, {champ.Draws}D, {champ.Losses}L)";
    }

    [McpServerTool, Description("Get aggregate statistics across the dataset: average goals per match, home win rate, total matches.")]
    public string GetAggregateStats(
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year. Optional.")] int? season = null)
    {
        _data.EnsureLoaded();
        var query = _data.Matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue)
            query = query.Where(m => m.Season == season);

        var withScores = query.Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue).ToList();
        if (withScores.Count == 0)
            return "No completed matches found for the criteria.";

        var totalGoals = withScores.Sum(m => m.HomeGoals!.Value + m.AwayGoals!.Value);
        var homeWins = withScores.Count(m => m.HomeWin);
        var awayWins = withScores.Count(m => m.AwayWin);
        var draws = withScores.Count(m => m.Draw);

        return $"Aggregate statistics ({withScores.Count} matches):\n" +
               $"- Average goals per match: {(double)totalGoals / withScores.Count:F2}\n" +
               $"- Home win rate: {(double)homeWins / withScores.Count * 100:F1}%\n" +
               $"- Away win rate: {(double)awayWins / withScores.Count * 100:F1}%\n" +
               $"- Draw rate: {(double)draws / withScores.Count * 100:F1}%\n" +
               $"- Total goals: {totalGoals}";
    }

    [McpServerTool, Description("Find the biggest victories (largest goal margins) in the dataset.")]
    public string GetBiggestVictories(
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Number of results. Default 10.")] int limit = 10)
    {
        _data.EnsureLoaded();
        var results = _data.BiggestVictories(limit, competition);
        if (results.Count == 0)
            return "No victories found.";

        var lines = results.Select((m, i) => $"{i + 1}. {m.Summary} (margin: {m.GoalDifference})");
        return $"Biggest victories ({results.Count}):\n" + string.Join("\n", lines);
    }

    [McpServerTool, Description("List all known teams in the dataset, sorted alphabetically. Useful for discovering valid team names.")]
    public string ListTeams(
        [Description("Filter teams by name substring. Optional.")] string? filter = null,
        [Description("Maximum number of teams. Default 50.")] int limit = 50)
    {
        _data.EnsureLoaded();
        var teams = _data.AllTeams();
        if (!string.IsNullOrWhiteSpace(filter))
            teams = teams.Where(t => t.Contains(filter, StringComparison.OrdinalIgnoreCase)).ToList();

        var results = teams.Take(Math.Max(1, limit)).ToList();
        if (results.Count == 0)
            return "No teams found matching the filter.";

        return $"Teams ({results.Count} of {teams.Count}):\n" + string.Join(", ", results);
    }
}
