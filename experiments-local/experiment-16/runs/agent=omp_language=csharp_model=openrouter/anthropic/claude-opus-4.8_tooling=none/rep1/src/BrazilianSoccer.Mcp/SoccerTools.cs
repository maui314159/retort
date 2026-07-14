// =============================================================================
// Context: Brazilian Soccer MCP Server — MCP tool surface.
//
// Exposes the QueryEngine to an LLM as a set of MCP tools (stdio transport).
// Each [McpServerTool] method maps one capability group from the spec to a
// callable tool with described parameters and returns formatted text. The shared
// QueryEngine is resolved from DI (constructed once at startup from the loaded
// datasets). Competition strings from the model are parsed leniently into
// CompetitionFilter so callers can pass "brasileirao", "serie a", "copa do
// brasil", "libertadores", etc.
// =============================================================================
using System.ComponentModel;
using BrazilianSoccer.Core;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Mcp;

[McpServerToolType]
public sealed class SoccerTools
{
    private readonly QueryEngine _engine;

    public SoccerTools(QueryEngine engine) => _engine = engine;

    [McpServerTool(Name = "find_matches")]
    [Description("Find soccer matches by team, opponent, season, date range, and/or competition. " +
        "A single team matches home or away; providing both team and opponent returns only head-to-head fixtures. " +
        "Includes a head-to-head summary when two teams are given.")]
    public string FindMatches(
        [Description("Team name to search for (matches home or away). Optional.")] string? team = null,
        [Description("Opponent team name; when set, only matches between team and opponent are returned. Optional.")] string? opponent = null,
        [Description("Season year, e.g. 2019. Optional.")] int? season = null,
        [Description("Competition: brasileirao, serie a, serie b, serie c, copa do brasil, or libertadores. Optional.")] string? competition = null,
        [Description("Start date (inclusive), ISO yyyy-MM-dd. Optional.")] string? fromDate = null,
        [Description("End date (inclusive), ISO yyyy-MM-dd. Optional.")] string? toDate = null,
        [Description("Max matches to return (default 25).")] int limit = 25)
    {
        var comp = ParseCompetition(competition);
        var matches = _engine.FindMatches(team, opponent, season,
            Parsing.Date(fromDate), Parsing.Date(toDate), comp, limit);

        var title = BuildMatchTitle(team, opponent, season, comp);
        var text = Format.Matches(matches, title, limit);

        if (team is not null && opponent is not null && matches.Count > 0)
        {
            var h2h = _engine.HeadToHeadFor(team, opponent, season, comp);
            text += "\n\n" + Format.HeadToHead(h2h);
        }
        return text;
    }

    [McpServerTool(Name = "team_record")]
    [Description("Get a team's win/draw/loss record, goals for/against, points, and win rate. " +
        "Optionally filter by season, competition, and venue (home/away/both).")]
    public string TeamRecord(
        [Description("Team name.")] string team,
        [Description("Season year, e.g. 2022. Optional.")] int? season = null,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Venue: home, away, or both (default both).")] string venue = "both")
    {
        var comp = ParseCompetition(competition);
        var va = ParseVenue(venue);
        var rec = _engine.TeamRecordFor(team, season, comp, va);
        var heading = BuildRecordHeading(rec.Team, season, comp, va);
        return Format.TeamRecord(rec, heading);
    }

    [McpServerTool(Name = "head_to_head")]
    [Description("Compare two teams head-to-head: matches played, wins for each side, draws, and goals.")]
    public string HeadToHead(
        [Description("First team name.")] string teamA,
        [Description("Second team name.")] string teamB,
        [Description("Season year. Optional.")] int? season = null,
        [Description("Competition filter. Optional.")] string? competition = null)
    {
        var comp = ParseCompetition(competition);
        var h = _engine.HeadToHeadFor(teamA, teamB, season, comp);
        if (h.Matches == 0)
            return $"No matches found between '{teamA}' and '{teamB}' in the dataset.";
        return Format.HeadToHead(h);
    }

    [McpServerTool(Name = "find_players")]
    [Description("Search FIFA players by name substring, nationality (e.g. Brazil), club, and/or position. " +
        "Results are sorted by Overall rating descending. Use this for questions like " +
        "'top Brazilian players' or 'players at Flamengo'.")]
    public string FindPlayers(
        [Description("Name substring. Optional.")] string? name = null,
        [Description("Nationality, e.g. Brazil. Optional.")] string? nationality = null,
        [Description("Club name. Optional.")] string? club = null,
        [Description("Position code, e.g. ST, GK, CB. Optional.")] string? position = null,
        [Description("Max players to return (default 20).")] int limit = 20)
    {
        var players = _engine.FindPlayers(name, nationality, club, position, limit);
        var title = BuildPlayerTitle(name, nationality, club, position);
        return Format.Players(players, title, limit);
    }

    [McpServerTool(Name = "player_profile")]
    [Description("Get the full profile of a single player by name (best match by rating). " +
        "Returns nationality, age, overall/potential, position, club, and physical attributes.")]
    public string PlayerProfile(
        [Description("Player name or substring.")] string name)
    {
        var players = _engine.FindPlayers(name: name, limit: 1);
        if (players.Count == 0)
            return $"No player found matching '{name}'.";
        return Format.PlayerProfile(players[0]);
    }

    [McpServerTool(Name = "standings")]
    [Description("Calculate the final league table for a competition and season from match results. " +
        "Defaults to Brasileirão Série A. Sorted by points, then goal difference. The leader is marked Champion.")]
    public string Standings(
        [Description("Season year, e.g. 2019.")] int season,
        [Description("Competition: serie a (default), serie b, serie c.")] string? competition = null,
        [Description("Max rows (default 30).")] int limit = 30)
    {
        var comp = competition is null ? CompetitionFilter.BrasileiraoSerieA : ParseCompetition(competition);
        if (comp == CompetitionFilter.Any) comp = CompetitionFilter.BrasileiraoSerieA;
        var rows = _engine.Standings(season, comp);
        var label = Format.CompetitionLabel(QueryEngine.ToCompetition(comp));
        return Format.Standings(rows, $"{season} {label} Final Standings (calculated from matches):", limit);
    }

    [McpServerTool(Name = "competition_stats")]
    [Description("Aggregate statistics over a match set: total matches, average goals per match, " +
        "home/away win rates, and draw rate. Optionally filter by season and competition.")]
    public string CompetitionStats(
        [Description("Season year. Optional.")] int? season = null,
        [Description("Competition filter. Optional.")] string? competition = null)
    {
        var comp = ParseCompetition(competition);
        var s = _engine.Stats(season, comp);
        var scope = BuildScope(season, comp);
        return Format.Stats(s, $"Statistics {scope}:");
    }

    [McpServerTool(Name = "biggest_wins")]
    [Description("List the biggest victories (largest goal margin) in the dataset, " +
        "optionally filtered by season and competition.")]
    public string BiggestWins(
        [Description("Season year. Optional.")] int? season = null,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Max matches (default 10).")] int limit = 10)
    {
        var comp = ParseCompetition(competition);
        var matches = _engine.BiggestWins(season, comp, limit);
        return Format.Matches(matches, $"Biggest victories {BuildScope(season, comp)}:", limit);
    }

    [McpServerTool(Name = "top_scoring_teams")]
    [Description("Rank teams by total goals scored over a season/competition. " +
        "Use for 'which team scored the most goals'.")]
    public string TopScoringTeams(
        [Description("Season year. Optional.")] int? season = null,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Max teams (default 10).")] int limit = 10)
    {
        var comp = ParseCompetition(competition);
        var teams = _engine.TopScorers(season, comp, limit);
        if (teams.Count == 0)
            return "No data available for the requested scope.";
        var lines = teams.Select((t, i) =>
            $"{i + 1}. {t.Team} - {t.GoalsFor} goals in {t.Matches} matches (GD {(t.GoalDifference >= 0 ? "+" : "")}{t.GoalDifference})");
        return $"Top scoring teams {BuildScope(season, comp)}:\n" + string.Join("\n", lines);
    }

    [McpServerTool(Name = "best_away_records")]
    [Description("Rank teams by away win rate (with a minimum match threshold). " +
        "Use for 'which team has the best away record'.")]
    public string BestAwayRecords(
        [Description("Season year. Optional.")] int? season = null,
        [Description("Competition filter. Optional.")] string? competition = null,
        [Description("Minimum away matches to qualify (default 5).")] int minMatches = 5,
        [Description("Max teams (default 10).")] int limit = 10)
    {
        var comp = ParseCompetition(competition);
        var teams = _engine.BestAwayRecords(season, comp, minMatches, limit);
        if (teams.Count == 0)
            return "No data available for the requested scope.";
        var lines = teams.Select((t, i) =>
            $"{i + 1}. {t.Team} - {(t.WinRate * 100):0.0}% ({t.Wins}W, {t.Draws}D, {t.Losses}L away)");
        return $"Best away records {BuildScope(season, comp)}:\n" + string.Join("\n", lines);
    }

    [McpServerTool(Name = "dataset_overview")]
    [Description("Summarize what data is loaded: total matches, players, and the competitions and seasons covered.")]
    public string DatasetOverview()
    {
        var seasons = _engine.SeasonsFor();
        var span = seasons.Count == 0 ? "n/a" : $"{seasons[0]}–{seasons[^1]}";
        return $"Loaded {_engine.MatchCount} matches and {_engine.PlayerCount} players.\n" +
               $"Seasons covered: {span}.\n" +
               "Competitions: Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores.";
    }

    // ---- parsing / titles -------------------------------------------------

    internal static CompetitionFilter ParseCompetition(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return CompetitionFilter.Any;
        var s = TeamName.FoldAccents(raw).Trim().ToLowerInvariant();
        if (s.Contains("libertadores")) return CompetitionFilter.Libertadores;
        if (s.Contains("copa") || s.Contains("cup")) return CompetitionFilter.CopaDoBrasil;
        if (s.Contains("serie b") || s == "b") return CompetitionFilter.BrasileiraoSerieB;
        if (s.Contains("serie c") || s == "c") return CompetitionFilter.BrasileiraoSerieC;
        if (s.Contains("serie a") || s.Contains("brasileirao") || s.Contains("brasileiro") || s == "a")
            return CompetitionFilter.BrasileiraoSerieA;
        return CompetitionFilter.Any;
    }

    private static HomeAway ParseVenue(string? raw)
    {
        var s = raw?.Trim().ToLowerInvariant();
        return s switch { "home" => HomeAway.Home, "away" => HomeAway.Away, _ => HomeAway.Both };
    }

    private static string BuildScope(int? season, CompetitionFilter comp)
    {
        var parts = new List<string>();
        if (comp != CompetitionFilter.Any)
            parts.Add($"in {Format.CompetitionLabel(QueryEngine.ToCompetition(comp))}");
        if (season.HasValue)
            parts.Add($"({season})");
        return parts.Count == 0 ? "(all data)" : string.Join(" ", parts);
    }

    private static string BuildMatchTitle(string? team, string? opponent, int? season, CompetitionFilter comp)
    {
        string subject = (team, opponent) switch
        {
            (not null, not null) => $"{team} vs {opponent} matches",
            (not null, null) => $"{team} matches",
            _ => "Matches",
        };
        return subject + " " + BuildScope(season, comp) + ":";
    }

    private static string BuildRecordHeading(string team, int? season, CompetitionFilter comp, HomeAway venue)
    {
        var v = venue switch { HomeAway.Home => "home ", HomeAway.Away => "away ", _ => "" };
        return $"{team} {v}record {BuildScope(season, comp)}:";
    }

    private static string BuildPlayerTitle(string? name, string? nationality, string? club, string? position)
    {
        var bits = new List<string>();
        if (position is not null) bits.Add(position);
        if (nationality is not null) bits.Add(nationality);
        bits.Add("players");
        if (club is not null) bits.Add($"at {club}");
        if (name is not null) bits.Add($"matching '{name}'");
        return string.Join(" ", bits) + ":";
    }
}
