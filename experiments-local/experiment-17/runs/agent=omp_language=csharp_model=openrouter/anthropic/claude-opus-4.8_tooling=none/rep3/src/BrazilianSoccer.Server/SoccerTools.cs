// =============================================================================
// File:    SoccerTools.cs
// Project: BrazilianSoccer.Server
// Purpose: MCP tool surface for the Brazilian Soccer knowledge graph. Each
//          [McpServerTool] method maps a TASK.md capability to a callable tool
//          an LLM client can invoke over stdio: match search, team records,
//          head-to-head, player search, league standings, statistics, biggest
//          wins, best home/away records, and competitions-for-team.
// Context: Tools are thin adapters — they parse string arguments (competition
//          names via CompetitionParser, dates via DateTime.TryParse), call the
//          shared SoccerDatabase (injected as a singleton, see Program.cs) and
//          return formatted text from AnswerFormatter. Returning preformatted
//          text keeps the contract simple for the connected LLM while every
//          numeric figure is computed from the loaded CSVs.
// =============================================================================

using System.ComponentModel;
using System.Globalization;
using BrazilianSoccer.Core;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Server;

[McpServerToolType]
public sealed class SoccerTools
{
    private readonly SoccerDatabase _db;

    public SoccerTools(SoccerDatabase db) => _db = db;

    [McpServerTool(Name = "find_matches")]
    [Description("Find soccer matches by team, opponent, competition, season, or date range. " +
                 "Provide team and opponent together for head-to-head fixtures.")]
    public string FindMatches(
        [Description("Team name (any spelling, e.g. 'Flamengo' or 'Palmeiras-SP'). Optional.")] string? team = null,
        [Description("Opponent team name to restrict to fixtures between the two teams. Optional.")] string? opponent = null,
        [Description("Competition: Brasileirao / Serie A / Serie B / Serie C / Copa do Brasil / Libertadores. Optional.")] string? competition = null,
        [Description("Season year, e.g. 2019. Optional.")] int? season = null,
        [Description("Start date (yyyy-MM-dd) inclusive. Optional.")] string? from = null,
        [Description("End date (yyyy-MM-dd) inclusive. Optional.")] string? to = null,
        [Description("Max matches to list (default 25).")] int limit = 25)
    {
        var matches = _db.FindMatches(team, opponent,
            CompetitionParser.Parse(competition), season,
            ParseDate(from), ParseDate(to));
        return AnswerFormatter.Matches(matches, limit);
    }

    [McpServerTool(Name = "head_to_head")]
    [Description("Head-to-head summary between two teams: wins, draws, goals and the match list.")]
    public string HeadToHead(
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year filter. Optional.")] int? season = null)
    {
        var h2h = _db.HeadToHead(teamA, teamB, CompetitionParser.Parse(competition), season);
        if (h2h is null) return $"No data found for {teamA} vs {teamB}.";
        if (h2h.Played == 0) return $"No matches between {h2h.TeamA} and {h2h.TeamB} in the dataset.";
        return AnswerFormatter.HeadToHead(h2h);
    }

    [McpServerTool(Name = "team_record")]
    [Description("Win/draw/loss record and goals for a team, optionally by season, competition, home or away.")]
    public string TeamRecord(
        [Description("Team name.")] string team,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year filter. Optional.")] int? season = null,
        [Description("Set true for home matches only.")] bool homeOnly = false,
        [Description("Set true for away matches only.")] bool awayOnly = false)
    {
        var comp = CompetitionParser.Parse(competition);
        var record = _db.TeamRecord(team, comp, season, homeOnly, awayOnly);
        if (record is null || record.Played == 0) return $"No record found for {team}.";

        var parts = new List<string>();
        if (homeOnly) parts.Add("home");
        if (awayOnly) parts.Add("away");
        if (season is not null) parts.Add(season.Value.ToString());
        if (comp is not null) parts.Add(comp.Value.DisplayName());
        var context = parts.Count > 0 ? $"record ({string.Join(" ", parts)})" : "overall record";
        return AnswerFormatter.TeamRecord(record, context);
    }

    [McpServerTool(Name = "find_players")]
    [Description("Search FIFA player data by name, nationality (e.g. 'Brazil'), club, or position. " +
                 "Results are sorted by overall rating, highest first.")]
    public string FindPlayers(
        [Description("Name substring to search for. Optional.")] string? name = null,
        [Description("Nationality, e.g. 'Brazil'. Optional.")] string? nationality = null,
        [Description("Club name (any spelling). Optional.")] string? club = null,
        [Description("Position code, e.g. 'GK', 'ST', 'LW'. Optional.")] string? position = null,
        [Description("Max players to return (default 20).")] int limit = 20)
    {
        var players = _db.FindPlayers(name, nationality, club, position, limit);
        var title = BuildPlayerTitle(name, nationality, club, position);
        return AnswerFormatter.Players(players, title, limit);
    }

    [McpServerTool(Name = "league_standings")]
    [Description("Calculated final league table for a competition and season (3 pts win, 1 draw).")]
    public string LeagueStandings(
        [Description("Season year, e.g. 2019.")] int season,
        [Description("Competition (default Brasileirao Serie A).")] string? competition = null,
        [Description("Number of rows to show (default 30).")] int limit = 30)
    {
        var comp = CompetitionParser.Parse(competition) ?? Competition.BrasileiraoSerieA;
        var table = _db.Standings(comp, season);
        return AnswerFormatter.Standings(table, comp, season, limit);
    }

    [McpServerTool(Name = "goal_statistics")]
    [Description("Average goals per match and home-win rate over a filtered set of matches.")]
    public string GoalStatistics(
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year filter. Optional.")] int? season = null)
    {
        var comp = CompetitionParser.Parse(competition);
        var (matches, avg, homeWin) = _db.GoalStats(comp, season);
        if (matches == 0) return "No scored matches found for that filter.";
        var ctx = Describe(comp, season);
        return AnswerFormatter.GoalStats(matches, avg, homeWin, ctx);
    }

    [McpServerTool(Name = "biggest_wins")]
    [Description("Largest-margin victories in the dataset, optionally filtered by competition and season.")]
    public string BiggestWins(
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year filter. Optional.")] int? season = null,
        [Description("How many to list (default 10).")] int limit = 10)
    {
        var comp = CompetitionParser.Parse(competition);
        var wins = _db.BiggestWins(comp, season, limit);
        return AnswerFormatter.Matches(wins, limit, $"Biggest victories {Describe(comp, season)}:");
    }

    [McpServerTool(Name = "best_records")]
    [Description("Rank teams by home or away win rate, optionally by competition and season.")]
    public string BestRecords(
        [Description("Set true for away records, false for home (default home).")] bool away = false,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Season year filter. Optional.")] int? season = null,
        [Description("Minimum matches played to qualify (default 5).")] int minPlayed = 5,
        [Description("How many teams to list (default 10).")] int limit = 10)
    {
        var comp = CompetitionParser.Parse(competition);
        var records = _db.BestRecords(homeOnly: !away, comp, season, minPlayed, limit);
        var which = away ? "away" : "home";
        return AnswerFormatter.TeamRanking(records, $"Best {which} records {Describe(comp, season)}:");
    }

    [McpServerTool(Name = "team_competitions")]
    [Description("List the competitions a team has appeared in, with match counts.")]
    public string TeamCompetitions(
        [Description("Team name.")] string team)
    {
        var comps = _db.CompetitionsForTeam(team);
        if (comps.Count == 0) return $"No matches found for {team}.";
        var lines = comps.Select(c => $"- {c.Competition.DisplayName()}: {c.Matches} matches");
        return $"Competitions for {_db.ResolveDisplayName(team)}:\n{string.Join('\n', lines)}";
    }

    // --- helpers -------------------------------------------------------------

    private static DateTime? ParseDate(string? s) =>
        !string.IsNullOrWhiteSpace(s) &&
        DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)
            ? dt : null;

    private static string Describe(Competition? comp, int? season)
    {
        var parts = new List<string>();
        if (comp is not null) parts.Add($"in {comp.Value.DisplayName()}");
        if (season is not null) parts.Add($"({season})");
        return parts.Count == 0 ? "(all data)" : string.Join(" ", parts);
    }

    private static string BuildPlayerTitle(string? name, string? nationality, string? club, string? position)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(position)) parts.Add(position!);
        if (!string.IsNullOrWhiteSpace(nationality)) parts.Add($"{nationality}");
        var who = parts.Count > 0 ? string.Join(" ", parts) + " players" : "Players";
        if (!string.IsNullOrWhiteSpace(name)) who += $" matching '{name}'";
        if (!string.IsNullOrWhiteSpace(club)) who += $" at {NameNormalizer.Display(club)}";
        return who + " (by overall rating):";
    }
}
