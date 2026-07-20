// =============================================================================
// File: Tools/BrazilianSoccerTools.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   The MCP tool surface. Each [McpServerTool] method is auto-discovered by
//   the MCP C# SDK (WithToolsFromAssembly in Program.cs) and exposed to LLM
//   clients over the stdio JSON-RPC transport.
//
//   Tools map 1:1 onto the spec's five capability categories:
//     Match Queries      -> search_matches, matches_between_teams
//     Team Queries       -> team_statistics, compare_teams, team_competitions,
//                           team_match_history
//     Player Queries     -> search_players, top_players, roster_summary
//     Competition Queries-> standings, competition_info, find_finals
//     Statistical Analysis-> average_goals, biggest_wins, top_scoring_teams,
//                            home_away_performance
//
//   Every tool returns a POCO (or List of POCOs). The MCP SDK serialises the
//   return value into the tool's structuredContent field so the LLM receives
//   both a readable text rendering and machine-parseable JSON.
//
//   Team/date/competition inputs are tolerant: team names run through the
//   TeamNameNormalizer (so "Palmeiras-SP" == "Palmeiras"), dates accept
//   ISO yyyy-MM-dd, and competitions accept friendly aliases ("Brasileirão",
//   "Copa do Brasil", "Libertadores", "Serie B", "Serie C").
// =============================================================================
namespace BrazilianSoccerMcp.Tools;

using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using BrazilianSoccerMcp.Query;
using ModelContextProtocol.Server;

[McpServerToolType]
public sealed class BrazilianSoccerTools
{
    private readonly MatchQueryService _matches;
    private readonly TeamQueryService _teams;
    private readonly PlayerQueryService _players;
    private readonly CompetitionQueryService _competitions;
    private readonly StatisticsService _stats;

    public BrazilianSoccerTools(
        MatchQueryService matches,
        TeamQueryService teams,
        PlayerQueryService players,
        CompetitionQueryService competitions,
        StatisticsService stats)
    {
        _matches = matches;
        _teams = teams;
        _players = players;
        _competitions = competitions;
        _stats = stats;
    }

    // ---------------------------------------------------------------------
    // 1. Match Queries
    // ---------------------------------------------------------------------
    [McpServerTool, Description(
        "Search Brazilian soccer matches. Filter by team (home or away), " +
        "opponent, competition (Brasileirão, Copa do Brasil, Libertadores, " +
        "Serie B, Serie C), season (e.g. 2023), and/or date range " +
        "(start_date/end_date as yyyy-MM-dd). Returns the most recent matches " +
        "first, capped at 'limit' (default 50).")]
    public List<MatchResultDto> SearchMatches(
        [Description("Team name, e.g. 'Flamengo' or 'Palmeiras-SP' (state suffix tolerated).")]
        string? team = null,
        [Description("Opponent team name to match against.")]
        string? opponent = null,
        [Description("Competition: 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'.")]
        string? competition = null,
        [Description("Season year, e.g. 2023.")]
        int? season = null,
        [Description("Start date inclusive, yyyy-MM-dd.")] string? startDate = null,
        [Description("End date inclusive, yyyy-MM-dd.")] string? endDate = null,
        [Description("Max matches to return (default 50).")] int limit = 50)
        => _matches.SearchMatches(team, opponent, competition, season,
            ParseDate(startDate), ParseDate(endDate), limit);

    [McpServerTool, Description(
        "Find all matches between two specific teams (e.g. Flamengo vs " +
        "Fluminense — the Fla-Flu derby). Optional competition / season " +
        "filters. Returns newest first.")]
    public List<MatchResultDto> MatchesBetweenTeams(
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Season filter, optional.")] int? season = null,
        [Description("Max matches (default 100).")] int limit = 100)
        => _matches.FindMatchesBetweenTeams(teamA, teamB, competition, season, limit);

    // ---------------------------------------------------------------------
    // 2. Team Queries
    // ---------------------------------------------------------------------
    [McpServerTool, Description(
        "Aggregated statistics for a team: matches, wins, draws, losses, " +
        "goals for/against, win rate. Optional season / competition / venue " +
        "('home', 'away', or 'both') filters.")]
    public TeamStatsDto TeamStatistics(
        [Description("Team name.")] string team,
        [Description("Season year, e.g. 2022.")] int? season = null,
        [Description("Competition filter.")] string? competition = null,
        [Description("Venue: 'home', 'away', or 'both' (default).")] string? venue = null)
        => _teams.GetTeamStatistics(team, season, competition, venue);

    [McpServerTool, Description(
        "Head-to-head comparison between two teams across all matches in the " +
        "dataset: wins/draws/losses, goals, and the most recent meetings.")]
    public HeadToHeadDto CompareTeams(
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Season filter, optional.")] int? season = null,
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Recent-match sample size (default 20).")] int limit = 20)
        => _teams.CompareTeams(teamA, teamB, season, competition, limit);

    [McpServerTool, Description(
        "Which competitions a team has played in, with match counts per " +
        "competition.")]
    public Dictionary<string, int> TeamCompetitions([Description("Team name.")] string team)
        => _teams.GetTeamCompetitions(team);

    [McpServerTool, Description(
        "Most recent matches for a team, newest first.")]
    public List<MatchResultDto> TeamMatchHistory(
        [Description("Team name.")] string team,
        [Description("Max matches (default 10).")] int limit = 10,
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Season filter, optional.")] int? season = null)
        => _teams.GetTeamMatchHistory(team, limit, competition, season);

    // ---------------------------------------------------------------------
    // 3. Player Queries
    // ---------------------------------------------------------------------
    [McpServerTool, Description(
        "Search FIFA player data by name, nationality, club, position, and/or " +
        "minimum overall rating. Example: top forwards at São Paulo, or all " +
        "Brazilian players. Sorted by overall rating descending.")]
    public List<PlayerResultDto> SearchPlayers(
        [Description("Name substring, e.g. 'Neymar'.")] string? name = null,
        [Description("Nationality substring, e.g. 'Brazil'.")] string? nationality = null,
        [Description("Club name, e.g. 'Flamengo' or 'Real Madrid'.")] string? club = null,
        [Description("Position code, e.g. 'ST', 'LW', 'CDM', 'GK'.")] string? position = null,
        [Description("Minimum FIFA overall rating.")] int? minOverall = null,
        [Description("Max players (default 50).")] int limit = 50)
        => _players.SearchPlayers(name, nationality, club, position, minOverall, limit);

    [McpServerTool, Description(
        "Top-N players by FIFA overall rating, optionally filtered by " +
        "nationality and/or club. E.g. top 10 Brazilian players, or " +
        "highest-rated players at Flamengo.")]
    public List<PlayerResultDto> TopPlayers(
        [Description("Number of players to return.")] int limit,
        [Description("Nationality filter, optional.")] string? nationality = null,
        [Description("Club filter, optional.")] string? club = null)
        => _players.GetTopPlayers(limit, nationality, club);

    [McpServerTool, Description(
        "Per-club roster summary for players of a given nationality. " +
        "Set brazilianClubsOnly=true to restrict to clubs that appear in the " +
        "Brazilian match data (i.e. Brazilian clubs) — matches the spec's " +
        "'Brazilian players at Brazilian clubs' example.")]
    public List<ClubRosterSummaryDto> RosterSummary(
        [Description("Nationality, e.g. 'Brazil'.")] string nationality,
        [Description("Restrict to Brazilian clubs (default true).")] bool brazilianClubsOnly = true,
        [Description("Max clubs (default 20).")] int limit = 20)
        => _players.GetClubRosterSummary(nationality, brazilianClubsOnly, limit);

    // ---------------------------------------------------------------------
    // 4. Competition Queries
    // ---------------------------------------------------------------------
    [McpServerTool, Description(
        "League standings for a competition + season, computed from match " +
        "results (3 pts win, 1 draw). Only league-format competitions have " +
        "standings: Brasileirão (Serie A), Serie B, Serie C. Sorted by points, " +
        "goal difference, then goals for.")]
    public List<StandingRowDto> Standings(
        [Description("Competition: 'Brasileirão', 'Serie B', 'Serie C'.")]
        string competition,
        [Description("Season year, e.g. 2019.")] int season)
        => _competitions.GetStandings(competition, season);

    [McpServerTool, Description(
        "Summary of a competition (and optional season): match count, rounds, " +
        "and date range.")]
    public CompetitionInfoDto CompetitionInfo(
        [Description("Competition name.")] string competition,
        [Description("Season year, optional.")] int? season = null)
        => _competitions.GetCompetitionInfo(competition, season);

    [McpServerTool, Description(
        "Find knockout finals (matches whose round/stage mentions 'final'). " +
        "Useful for 'Find all Copa do Brasil finals'.")]
    public List<MatchResultDto> FindFinals(
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Season filter, optional.")] int? season = null,
        [Description("Max results (default 50).")] int limit = 50)
        => _competitions.FindFinals(competition, season, limit);

    // ---------------------------------------------------------------------
    // 5. Statistical Analysis
    // ---------------------------------------------------------------------
    [McpServerTool, Description(
        "Average goals per match plus home-win / away-win / draw rates for a " +
        "competition (optionally season-scoped).")]
    public GoalsStatsDto AverageGoals(
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Season filter, optional.")] int? season = null)
        => _stats.GetAverageGoals(competition, season);

    [McpServerTool, Description(
        "Biggest victories in the dataset, ranked by goal margin. Optional " +
        "competition / season filters.")]
    public List<BiggestWinDto> BiggestWins(
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Season filter, optional.")] int? season = null,
        [Description("Max results (default 20).")] int limit = 20)
        => _stats.GetBiggestWins(competition, season, limit);

    [McpServerTool, Description(
        "Top-scoring teams (by total goals for) in a league competition + " +
        "season.")]
    public List<TeamScoringDto> TopScoringTeams(
        [Description("Competition: 'Brasileirão', 'Serie B', 'Serie C'.")]
        string competition,
        [Description("Season year.")] int season,
        [Description("Max teams (default 10).")] int limit = 10)
        => _stats.GetTopScoringTeams(competition, season, limit);

    [McpServerTool, Description(
        "Home vs away win/draw rates for a competition (optionally " +
        "season-scoped). Same figures as average_goals but presented for " +
        "home/away split questions.")]
    public GoalsStatsDto HomeAwayPerformance(
        [Description("Competition filter, optional.")] string? competition = null,
        [Description("Season filter, optional.")] int? season = null)
        => _stats.GetHomeAwayPerformance(competition, season);

    // ---------------------------------------------------------------------
    private static DateTime? ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        if (DateTime.TryParseExact(raw.Trim(), "yyyy-MM-dd",
                CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal,
                out var dt))
            return dt;
        return null;
    }
}
