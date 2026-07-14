using System.ComponentModel;
using System.Globalization;
using BrazilianSoccerMcpServer.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcpServer.Tools;

[McpServerToolType]
public static class SoccerTools
{
    [McpServerTool, Description("Search for matches across all Brazilian soccer datasets. Filters by team, opponent, competition, season, and date range.")]
    public static string SearchMatches(
        SoccerDataService service,
        [Description("Team name to search for (home or away).")] string? team = null,
        [Description("Opponent team name to narrow results.")] string? opponent = null,
        [Description("Competition filter: Brasileirão, Copa do Brasil, or Copa Libertadores.")] string? competition = null,
        [Description("Season year filter.")] int? season = null,
        [Description("Start date (yyyy-MM-dd).")] string? fromDate = null,
        [Description("End date (yyyy-MM-dd).")] string? toDate = null,
        [Description("Maximum number of matches to return."),] int limit = 50)
    {
        var from = ParseDate(fromDate);
        var to = ParseDate(toDate);
        var matches = service.FindMatches(team, opponent, competition, season, from, to, limit).ToList();

        if (matches.Count == 0)
        {
            return "No matches found for the requested criteria.";
        }

        return string.Join("\n", matches.Select(m => $"- {m.FormatShort()}"));
    }

    [McpServerTool, Description("Get win/loss/draw statistics for a team, optionally filtered by season, competition, and venue.")]
    public static string GetTeamStatistics(
        SoccerDataService service,
        [Description("Team name (e.g., Palmeiras, Flamengo, Corinthians).")] string team,
        [Description("Season year filter.")] int? season = null,
        [Description("Competition filter: Brasileirão, Copa do Brasil, or Copa Libertadores.")] string? competition = null,
        [Description("Venue filter: home, away, or all (default all).")] string? venue = null)
    {
        var stats = service.GetTeamStats(team, season, competition, venue);
        return stats.Matches == 0
            ? $"No matches found for {stats.Team}."
            : stats.ToString();
    }

    [McpServerTool, Description("Get head-to-head record between two teams across all datasets.")]
    public static string GetHeadToHead(
        SoccerDataService service,
        [Description("First team name."),] string teamA,
        [Description("Second team name."),] string teamB)
    {
        var h2h = service.GetHeadToHead(teamA, teamB);
        return h2h.Matches == 0
            ? $"No head-to-head matches found between {teamA} and {teamB}."
            : h2h.ToString();
    }

    [McpServerTool, Description("Calculate league standings for a competition and season. Use season to restrict the calculation.")]
    public static string GetStandings(
        SoccerDataService service,
        [Description("Competition name: Brasileirão, Copa do Brasil, or Copa Libertadores.")] string competition,
        [Description("Season year."),] int? season = null,
        [Description("Maximum rows to return."),] int limit = 20)
    {
        var standings = service.GetStandings(competition, season).Take(limit).ToList();
        if (standings.Count == 0)
        {
            return $"No standings available for {competition}{(season.HasValue ? $" {season}" : string.Empty)}.";
        }

        var lines = standings.Select((s, i) => $"{i + 1}. {s}").ToList();
        if (standings.Count > 0 && season.HasValue)
        {
            lines[0] += " - Champion";
        }

        return string.Join("\n", lines);
    }

    [McpServerTool, Description("Find the biggest wins (largest goal difference) in the dataset.")]
    public static string GetBiggestWins(
        SoccerDataService service,
        [Description("Competition filter."),] string? competition = null,
        [Description("Number of results to return."),] int limit = 10)
    {
        var matches = service.GetBiggestWins(competition, limit).ToList();
        if (matches.Count == 0)
        {
            return "No matches found.";
        }

        return string.Join("\n", matches.Select(m => $"- {m.FormatShort()} (GD {Math.Abs(m.GoalDifference ?? 0)})"));
    }

    [McpServerTool, Description("Calculate the average goals per match, optionally filtered by competition and season.")]
    public static string GetAverageGoals(
        SoccerDataService service,
        [Description("Competition filter."),] string? competition = null,
        [Description("Season year."),] int? season = null)
    {
        var avg = service.GetAverageGoals(competition, season);
        var filter = string.Empty;
        if (!string.IsNullOrWhiteSpace(competition)) filter += $" in {competition}";
        if (season.HasValue) filter += $" {season}";
        return $"Average goals per match{filter}: {avg:F2}";
    }

    [McpServerTool, Description("Search the FIFA player database by name, nationality, club, position, and minimum overall rating.")]
    public static string SearchPlayers(
        SoccerDataService service,
        [Description("Player name (substring)."),] string? name = null,
        [Description("Nationality (e.g., Brazil)."),] string? nationality = null,
        [Description("Club name (substring or canonical name)."),] string? club = null,
        [Description("Position abbreviation (e.g., ST, LW, GK)."),] string? position = null,
        [Description("Minimum overall rating."),] int? minOverall = null,
        [Description("Maximum players to return."),] int limit = 20)
    {
        var players = service.SearchPlayers(name, nationality, club, position, minOverall, limit).ToList();
        if (players.Count == 0)
        {
            return "No players found for the requested criteria.";
        }

        return string.Join("\n", players.Select((p, i) => $"{i + 1}. {p.FormatShort()}"));
    }

    [McpServerTool, Description("Look up a player by name in the FIFA dataset.")]
    public static string GetPlayerByName(
        SoccerDataService service,
        [Description("Player name to look up.")] string name)
    {
        var player = service.GetPlayerByName(name);
        return player == null
            ? $"No player found matching '{name}'."
            : player.FormatShort();
    }

    [McpServerTool, Description("List all competitions available in the match datasets.")]
    public static string ListCompetitions(SoccerDataService service)
    {
        var competitions = service.ListCompetitions();
        return competitions.Count == 0
            ? "No competitions loaded."
            : string.Join("\n", competitions.Select(c => $"- {c}"));
    }

    private static DateTime? ParseDate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (DateTime.TryParseExact(value, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)) return dt;
        if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt)) return dt;
        return null;
    }
}
