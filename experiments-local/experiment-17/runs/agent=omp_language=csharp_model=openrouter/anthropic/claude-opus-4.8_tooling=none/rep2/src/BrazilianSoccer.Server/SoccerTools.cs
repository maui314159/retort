// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    SoccerTools.cs
// Project: BrazilianSoccer.Server
// Purpose: The MCP tool surface. Each [McpServerTool] method exposes one of the
//          spec's query capabilities to a connected LLM. Methods are thin: they
//          parse arguments, delegate to QueryService (injected via DI) and
//          render with ResponseFormatter.
// Mapping to spec capabilities:
//   1. Match queries        -> FindMatches, MatchesBetween, LastMatch
//   2. Team queries         -> TeamRecord, CompareTeams
//   3. Player queries       -> SearchPlayers, PlayersByNationality, PlayersByClub,
//                              TopPlayers
//   4. Competition queries  -> Standings, Champion
//   5. Statistical analysis -> Statistics, BiggestWins, TopScoringTeams
// =============================================================================

using System.ComponentModel;
using BrazilianSoccer.Core.Models;
using BrazilianSoccer.Core.Queries;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Server;

/// <summary>MCP tools answering Brazilian-soccer knowledge-graph queries.</summary>
[McpServerToolType]
public sealed class SoccerTools
{
    private static Competition? ParseCompetition(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return null;
        var n = name.Trim().ToLowerInvariant();
        return n switch
        {
            "brasileirao" or "brasileirão" or "serie a" or "série a" or "league" => Competition.Brasileirao,
            "copa do brasil" or "cup" or "brazilian cup" => Competition.CopaDoBrasil,
            "libertadores" or "copa libertadores" => Competition.Libertadores,
            _ => null,
        };
    }

    [McpServerTool(Name = "find_matches")]
    [Description("Find matches filtered by team, opponent, competition, season, and date range. " +
                 "Returns the most recent matches first. Competition values: 'Brasileirao', 'Copa do Brasil', 'Libertadores'.")]
    public static string FindMatches(
        QueryService query,
        [Description("Team name (matches home or away). Accepts variations like 'Flamengo' or 'Flamengo-RJ'.")] string? team = null,
        [Description("Competition name: Brasileirao, Copa do Brasil, or Libertadores.")] string? competition = null,
        [Description("Season year, e.g. 2019.")] int? season = null,
        [Description("Inclusive start date (yyyy-MM-dd).")] string? from = null,
        [Description("Inclusive end date (yyyy-MM-dd).")] string? to = null,
        [Description("Maximum matches to return (default 25).")] int limit = 25)
    {
        var filter = new MatchFilter
        {
            Team = team,
            Competition = ParseCompetition(competition),
            Season = season,
            From = TryDate(from),
            To = TryDate(to),
            Limit = limit,
        };
        var matches = query.FindMatches(filter);
        var title = $"Matches{(team is null ? "" : $" for {team}")}" +
                    $"{(competition is null ? "" : $" in {competition}")}" +
                    $"{(season is null ? "" : $" ({season})")}:";
        return ResponseFormatter.FormatMatches(title, matches, show: limit);
    }

    [McpServerTool(Name = "matches_between")]
    [Description("Find all matches between two teams (a rivalry / derby) with the head-to-head record.")]
    public static string MatchesBetween(
        QueryService query,
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB)
    {
        var h2h = query.HeadToHeadFor(teamA, teamB);
        return ResponseFormatter.FormatHeadToHead(h2h);
    }

    [McpServerTool(Name = "last_match")]
    [Description("Find the most recent match between two teams and its score.")]
    public static string LastMatch(
        QueryService query,
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB)
    {
        var match = query.LastMatchBetween(teamA, teamB);
        if (match is null)
            return $"No matches between {teamA} and {teamB} were found in the dataset.";
        return "Most recent meeting:\n- " + ResponseFormatter.MatchLine(match);
    }

    [McpServerTool(Name = "team_record")]
    [Description("Get a team's win/draw/loss record and goals, optionally filtered by competition, season and venue (home/away).")]
    public static string TeamRecord(
        QueryService query,
        [Description("Team name.")] string team,
        [Description("Competition name (optional).")] string? competition = null,
        [Description("Season year (optional).")] int? season = null,
        [Description("Venue filter: 'home', 'away', or omit for all.")] string? venue = null)
    {
        var filter = new MatchFilter
        {
            Team = team,
            Competition = ParseCompetition(competition),
            Season = season,
        };
        var record = query.TeamRecordFor(team, filter, NormalizeVenue(venue));
        var ctx = BuildContext(competition, season, venue);
        return ResponseFormatter.FormatTeamRecord(record, ctx);
    }

    [McpServerTool(Name = "compare_teams")]
    [Description("Compare two teams head-to-head: matches, wins each, draws, and goals.")]
    public static string CompareTeams(
        QueryService query,
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB)
        => ResponseFormatter.FormatHeadToHead(query.HeadToHeadFor(teamA, teamB));

    [McpServerTool(Name = "search_players")]
    [Description("Search FIFA players by (partial) name. Returns the highest-rated matches.")]
    public static string SearchPlayers(
        QueryService query,
        [Description("Player name or part of it.")] string name,
        [Description("Maximum players to return (default 25).")] int limit = 25)
    {
        var players = query.SearchPlayersByName(name, limit);
        if (players.Count == 1)
            return ResponseFormatter.FormatPlayer(players[0]);
        return ResponseFormatter.FormatPlayers($"Players matching '{name}':", players, limit);
    }

    [McpServerTool(Name = "players_by_nationality")]
    [Description("List FIFA players of a given nationality (e.g. 'Brazil'), highest-rated first.")]
    public static string PlayersByNationality(
        QueryService query,
        [Description("Nationality, e.g. 'Brazil'.")] string nationality,
        [Description("Maximum players to return (default 25).")] int limit = 25)
        => ResponseFormatter.FormatPlayers(
            $"Top {nationality} players in dataset:",
            query.PlayersByNationality(nationality, limit), limit);

    [McpServerTool(Name = "players_by_club")]
    [Description("List FIFA players at a given club (e.g. 'Flamengo'), highest-rated first.")]
    public static string PlayersByClub(
        QueryService query,
        [Description("Club name.")] string club,
        [Description("Maximum players to return (default 25).")] int limit = 25)
        => ResponseFormatter.FormatPlayers(
            $"Players at {club}:",
            query.PlayersByClub(club, limit), limit);

    [McpServerTool(Name = "top_players")]
    [Description("List the highest-rated players, optionally filtered by nationality and position.")]
    public static string TopPlayers(
        QueryService query,
        [Description("Maximum players to return (default 10).")] int limit = 10,
        [Description("Nationality filter (optional), e.g. 'Brazil'.")] string? nationality = null,
        [Description("Position filter (optional), e.g. 'ST', 'GK', 'LW'.")] string? position = null)
    {
        var players = query.TopPlayers(limit, nationality, position);
        var title = "Top-rated players" +
                    (nationality is null ? "" : $" ({nationality})") +
                    (position is null ? "" : $" at {position}") + ":";
        return ResponseFormatter.FormatPlayers(title, players, limit);
    }

    [McpServerTool(Name = "standings")]
    [Description("Calculate the final league standings for a competition and season from match results (3 pts win, 1 draw).")]
    public static string Standings(
        QueryService query,
        [Description("Competition name: Brasileirao, Copa do Brasil, or Libertadores.")] string competition,
        [Description("Season year, e.g. 2019.")] int season)
    {
        var comp = ParseCompetition(competition);
        if (comp is null)
            return $"Unknown competition '{competition}'. Use Brasileirao, Copa do Brasil, or Libertadores.";
        var rows = query.Standings(comp.Value, season);
        return ResponseFormatter.FormatStandings(
            $"{season} {comp.Value} final standings (calculated from matches):", rows);
    }

    [McpServerTool(Name = "champion")]
    [Description("Get the champion (top of the calculated table) for a competition and season.")]
    public static string Champion(
        QueryService query,
        [Description("Competition name.")] string competition,
        [Description("Season year.")] int season)
    {
        var comp = ParseCompetition(competition);
        if (comp is null)
            return $"Unknown competition '{competition}'.";
        var top = query.Champion(comp.Value, season);
        if (top is null)
            return $"No data for {comp.Value} {season} in the dataset.";
        var r = top.Record;
        return $"{season} {comp.Value} champion (calculated from matches): {r.Team} " +
               $"- {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L).";
    }

    [McpServerTool(Name = "statistics")]
    [Description("Aggregate statistics (average goals per match, home/away win rate, draw rate) for a slice of matches.")]
    public static string Statistics(
        QueryService query,
        [Description("Team filter (optional).")] string? team = null,
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season filter (optional).")] int? season = null)
    {
        var filter = new MatchFilter
        {
            Team = team,
            Competition = ParseCompetition(competition),
            Season = season,
        };
        var stats = query.ComputeStatistics(filter);
        var title = "Statistics" +
                    (team is null ? "" : $" for {team}") +
                    (competition is null ? "" : $" in {competition}") +
                    (season is null ? "" : $" ({season})") + ":";
        return ResponseFormatter.FormatStatistics(title, stats);
    }

    [McpServerTool(Name = "biggest_wins")]
    [Description("List the matches with the biggest goal margins, optionally filtered by competition and season.")]
    public static string BiggestWins(
        QueryService query,
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season filter (optional).")] int? season = null,
        [Description("Maximum matches to return (default 10).")] int limit = 10)
    {
        var filter = new MatchFilter
        {
            Competition = ParseCompetition(competition),
            Season = season,
        };
        var matches = query.BiggestWins(filter, limit);
        var title = "Biggest victories" +
                    (competition is null ? "" : $" in {competition}") +
                    (season is null ? "" : $" ({season})") + ":";
        return ResponseFormatter.FormatBiggestWins(title, matches);
    }

    [McpServerTool(Name = "top_scoring_teams")]
    [Description("Rank teams by total goals scored, optionally filtered by competition and season.")]
    public static string TopScoringTeams(
        QueryService query,
        [Description("Competition filter (optional).")] string? competition = null,
        [Description("Season filter (optional).")] int? season = null,
        [Description("Maximum teams to return (default 10).")] int limit = 10)
    {
        var filter = new MatchFilter
        {
            Competition = ParseCompetition(competition),
            Season = season,
        };
        var teams = query.TopScoringTeams(filter, limit);
        var title = "Top scoring teams" +
                    (competition is null ? "" : $" in {competition}") +
                    (season is null ? "" : $" ({season})") + ":";
        return ResponseFormatter.FormatTopScorers(title, teams);
    }

    private static DateTime? TryDate(string? raw)
        => DateTime.TryParse(raw, System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.None, out var d) ? d : null;

    private static string? NormalizeVenue(string? venue)
    {
        if (string.IsNullOrWhiteSpace(venue))
            return null;
        var v = venue.Trim().ToLowerInvariant();
        return v is "home" or "away" ? v : null;
    }

    private static string? BuildContext(string? competition, int? season, string? venue)
    {
        var parts = new List<string>();
        if (NormalizeVenue(venue) is { } v)
            parts.Add(v);
        parts.Add("record");
        var suffix = new List<string>();
        if (season is { } s) suffix.Add(s.ToString());
        if (!string.IsNullOrWhiteSpace(competition)) suffix.Add(competition.Trim());
        var core = string.Join(" ", parts);
        return suffix.Count > 0 ? $"{core} ({string.Join(" ", suffix)})" : core;
    }
}
