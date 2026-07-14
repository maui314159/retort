// BrazilianSoccerMcp.Server - MCP tools.
// Each [McpServerTool] method is exposed to the LLM over the MCP protocol.
// Tools are thin wrappers around SoccerQueryService + ResponseFormatter so all
// query logic lives in the testable Core library. The data directory defaults
// to ./data/kaggle relative to the server working directory but can be
// overridden via the BSOCCER_DATA environment variable.
using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Services;
using ModelContextProtocol.Server;
using System.ComponentModel;
using static BrazilianSoccerMcp.Server.Tools.ToolHelpers;

namespace BrazilianSoccerMcp.Server.Tools;

/// <summary>
/// Static holder of the lazily-initialized data facade. The MCP host
/// constructs tools on demand, so we load the datasets once and cache them.
/// </summary>
internal static class DataContext
{
    private static BrazilianSoccerData? _data;
    private static readonly object _gate = new();

    public static BrazilianSoccerData Data
    {
        get
        {
            if (_data is null)
            {
                lock (_gate)
                {
                    if (_data is null)
                    {
                        var dir = Environment.GetEnvironmentVariable("BSOCCER_DATA")
                                  ?? Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
                        _data = new BrazilianSoccerData(dir);
                    }
                }
            }
            return _data;
        }
    }

    public static SoccerQueryService Query => Data.Query;
}

/// <summary>Match queries: find matches by team, between teams, by date/competition/season.</summary>
[McpServerToolType]
public static class MatchTools
{
    [McpServerTool, Description("Find all matches for a team, optionally filtered by competition, season and/or date range. Competitions: Brasileirao, CopaDoBrasil, Libertadores, HistoricalBrasileirao, Other. Dates are ISO yyyy-MM-dd.")]
    public static string FindMatchesByTeam(
        string team,
        string? competition = null,
        int? season = null,
        string? from = null,
        string? to = null)
    {
        var comp = ParseCompetition(competition);
        var fromDt = ParseDate(from);
        var toDt = ParseDate(to);
        var matches = DataContext.Query.FindMatchesByTeam(team, comp, season, fromDt, toDt);
        var ctx = DescribeFilter(competition, season);
        return ResponseFormatter.FormatMatchList(matches, $"{DataContext.Query.ResolveTeam(team)} matches{ctx}");
    }

    [McpServerTool, Description("Find all matches between two teams (head-to-head fixtures), with optional competition/season filters. Returns the fixture list and the win/draw/loss tally.")]
    public static string FindMatchesBetweenTeams(
        string teamA, string teamB,
        string? competition = null, int? season = null)
    {
        var comp = ParseCompetition(competition);
        // Use the full head-to-head (across all competitions) for the
        // win/draw/loss tally, but list fixtures filtered by competition/season
        // when those parameters are supplied.
        var h2h = DataContext.Query.GetHeadToHead(teamA, teamB);
        var filtered = (comp is null && season is null)
            ? h2h.MatchesList
            : DataContext.Query.FindMatchesBetweenTeams(teamA, teamB, comp, season);
        return ResponseFormatter.FormatHeadToHead(h2h with { MatchesList = filtered, Matches = filtered.Count });
    }

    [McpServerTool, Description("Return the most recent match between two teams in the dataset, including the score and competition.")]
    public static string FindMostRecentMatch(string teamA, string teamB)
    {
        var m = DataContext.Query.FindMostRecentMatch(teamA, teamB);
        if (m is null) return $"No match found between {teamA} and {teamB}.";
        return $"Most recent match: {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.Score} {m.AwayTeam} ({CompetitionDisplay.Name(m.Competition)}{RoundOf(m)})";
    }

    [McpServerTool, Description("List all traditional derby matches (Fla-Flu, Majestoso, Grenal, etc.), optionally filtered by season/competition.")]
    public static string FindDerbies(int? season = null, string? competition = null)
    {
        var comp = ParseCompetition(competition);
        var derbies = DataContext.Query.FindDerbies(season, comp);
        return ResponseFormatter.FormatMatchList(derbies, "Derbies");
    }

    private static string RoundOf(Core.Models.Match m) =>
        string.IsNullOrEmpty(m.Round) ? (string.IsNullOrEmpty(m.Stage) ? "" : $" {m.Stage}") : $" Round {m.Round}";
}

/// <summary>Team queries: statistics, head-to-head, home/away records.</summary>
[McpServerToolType]
public static class TeamTools
{
    [McpServerTool, Description("Return win/draw/loss and goal statistics for a team, optionally filtered by competition and/or season.")]
    public static string GetTeamStats(string team, string? competition = null, int? season = null)
    {
        var comp = ParseCompetition(competition);
        var stats = DataContext.Query.GetTeamStats(team, comp, season);
        return ResponseFormatter.FormatTeamStats(stats, DescribeFilter(competition, season));
    }

    [McpServerTool, Description("Compare two teams head-to-head: wins, draws, losses and a list of their fixtures.")]
    public static string CompareTeamsHeadToHead(string teamA, string teamB)
    {
        var h2h = DataContext.Query.GetHeadToHead(teamA, teamB);
        return ResponseFormatter.FormatHeadToHead(h2h);
    }

    [McpServerTool, Description("Rank teams by home win rate (minimum matches threshold applies).")]
    public static string BestHomeRecords(string? competition = null, int? season = null, int minMatches = 10)
    {
        var comp = ParseCompetition(competition);
        var rows = DataContext.Query.BestHomeRecords(comp, season, minMatches).Take(20);
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Best home records:");
        int i = 1;
        foreach (var r in rows)
            sb.AppendLine($"{i}. {r.Team} - {r.HomeWinRate:P1} ({r.HomeWins}W/{r.HomeDraws}D/{r.HomeLosses}L in {r.HomeMatches} home matches)");
        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Rank teams by away win rate (minimum matches threshold applies).")]
    public static string BestAwayRecords(string? competition = null, int? season = null, int minMatches = 10)
    {
        var comp = ParseCompetition(competition);
        var rows = DataContext.Query.BestAwayRecords(comp, season, minMatches).Take(20);
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Best away records:");
        int i = 1;
        foreach (var r in rows)
            sb.AppendLine($"{i}. {r.Team} - {r.AwayWinRate:P1} ({r.AwayWins}W/{r.AwayDraws}D/{r.AwayLosses}L in {r.AwayMatches} away matches)");
        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Return the highest-scoring team by total goals, optionally filtered by competition/season.")]
    public static string TopScoringTeam(string? competition = null, int? season = null)
    {
        var comp = ParseCompetition(competition);
        var s = DataContext.Query.TopScoringTeam(comp, season);
        if (s is null) return "No data.";
        return $"Top scoring team{DescribeFilter(competition, season)}: {s.Team} with {s.GoalsFor} goals in {s.Matches} matches.";
    }
}

/// <summary>Competition queries: standings, available seasons.</summary>
[McpServerToolType]
public static class CompetitionTools
{
    [McpServerTool, Description("Calculate and return the final standings table for a season of a competition. Competitions: Brasileirao, CopaDoBrasil, Libertadores, HistoricalBrasileirao.")]
    public static string GetStandings(int season, string competition)
    {
        var comp = ParseCompetition(competition) ?? Competition.Brasileirao;
        var rows = DataContext.Query.GetStandings(season, comp);
        return ResponseFormatter.FormatStandings(rows, season, comp);
    }

    [McpServerTool, Description("List all seasons available in the dataset, optionally filtered by competition.")]
    public static string AvailableSeasons(string? competition = null)
    {
        var comp = ParseCompetition(competition);
        var seasons = DataContext.Query.AvailableSeasons(comp).ToList();
        return $"Available seasons{(comp.HasValue ? $" for {CompetitionDisplay.Name(comp.Value)}" : "")}: {string.Join(", ", seasons)}";
    }
}

/// <summary>Player queries: search FIFA data by name, nationality, club, position, rating.</summary>
[McpServerToolType]
public static class PlayerTools
{
    [McpServerTool, Description("Search FIFA player data. Filter by name (substring), nationality, club (substring), position, and overall rating range. Returns the top matches sorted by overall rating.")]
    public static string FindPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? maxOverall = null,
        int top = 20)
    {
        var players = DataContext.Query.FindPlayers(name, nationality, club, position, minOverall, maxOverall, top);
        var title = string.IsNullOrWhiteSpace(name) ? "Player search results" : $"Players matching '{name}'";
        return ResponseFormatter.FormatPlayers(players, title);
    }

    [McpServerTool, Description("Return the top-N highest-rated Brazilian players in the FIFA dataset.")]
    public static string TopBrazilianPlayers(int top = 10)
        => ResponseFormatter.FormatPlayers(DataContext.Query.TopBrazilianPlayers(top), "Top-rated Brazilian players in dataset");

    [McpServerTool, Description("Return all players at a given club (substring match on club name), sorted by overall rating.")]
    public static string PlayersAtClub(string club, int top = 30)
        => ResponseFormatter.FormatPlayers(DataContext.Query.PlayersAtClub(club, top), $"Players at {club}");
}

/// <summary>Statistical analysis across the datasets.</summary>
[McpServerToolType]
public static class StatsTools
{
    [McpServerTool, Description("Return the biggest victories (by goal difference) plus average goals per match and home/draw/away win rates. Optional competition/season filters.")]
    public static string BiggestVictories(string? competition = null, int? season = null, int top = 10)
    {
        var comp = ParseCompetition(competition);
        var wins = DataContext.Query.BiggestWins(comp, season, top);
        var avg = DataContext.Query.AverageGoalsPerMatch(comp, season);
        var rates = DataContext.Query.WinRateBreakdown(comp, season);
        return ResponseFormatter.FormatBiggestWins(wins, avg, rates);
    }

    [McpServerTool, Description("Return the average goals per match, plus home win / draw / away win rates, optionally filtered.")]
    public static string MatchAverages(string? competition = null, int? season = null)
    {
        var comp = ParseCompetition(competition);
        var avg = DataContext.Query.AverageGoalsPerMatch(comp, season);
        var rates = DataContext.Query.WinRateBreakdown(comp, season);
        return $"Average goals per match: {avg:F2}\nHome win rate: {rates.HomeWinRate:P1}, Draw rate: {rates.DrawRate:P1}, Away win rate: {rates.AwayWinRate:P1}";
    }
}

// ---- Shared helpers --------------------------------------------------------

internal static class ToolHelpers
{
    public static Competition? ParseCompetition(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return raw.Trim().ToLowerInvariant() switch
        {
            "brasileirao" or "seriea" or "serie a" or "brasileirao serie a" => Competition.Brasileirao,
            "copadobrasil" or "copa do brasil" or "copa" or "braziliancup" => Competition.CopaDoBrasil,
            "libertadores" or "copalibertadores" => Competition.Libertadores,
            "historical" or "historicalbrasileirao" or "2003-2019" => Competition.HistoricalBrasileirao,
            "other" or "brfootball" or "extended" => Competition.Other,
            _ => null
        };
    }

    public static DateTime? ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return BrazilianSoccerMcp.Core.Data.DateParser.Parse(raw);
    }

    public static string DescribeFilter(string? competition, int? season)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(competition)) parts.Add(competition);
        if (season.HasValue) parts.Add(season.Value.ToString());
        return parts.Count == 0 ? "" : $" ({string.Join(" ", parts)})";
    }
}
