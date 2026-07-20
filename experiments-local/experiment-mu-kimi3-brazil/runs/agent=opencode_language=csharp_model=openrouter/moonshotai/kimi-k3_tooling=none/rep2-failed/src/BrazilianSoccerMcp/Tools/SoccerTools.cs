// Context: Brazilian Soccer MCP Server.
// MCP tool surface. Thin formatting wrappers over SoccerQueryEngine — every
// tool answers one category from the specification (matches, teams, players,
// competitions, statistics). Team/competition/date parameters are free text:
// the engine normalizes team names ("palmeiras", "Palmeiras-SP", ...),
// competition aliases ("Serie A", "libertadores") and ISO dates.
namespace BrazilianSoccerMcp.Tools;

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Query;
using ModelContextProtocol.Server;

[McpServerToolType]
public sealed class SoccerTools
{
    private readonly SoccerQueryEngine _engine;
    public SoccerTools(SoccerQueryEngine engine) => _engine = engine;

    [McpServerTool(Name = "find_matches")]
    [Description("Find soccer matches by team (home/away/either), opponent, competition (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), season and/or date range.")]
    public string FindMatches(
        [Description("Team name in any spelling, e.g. 'Flamengo', 'Palmeiras-SP'")] string? team = null,
        [Description("Opponent team name, for matches between two teams")] string? opponent = null,
        [Description("Competition name or alias, e.g. 'Serie A', 'Copa do Brasil', 'Libertadores'")] string? competition = null,
        [Description("Season year, e.g. 2023")] int? season = null,
        [Description("Start date (yyyy-MM-dd)")] string? fromDate = null,
        [Description("End date (yyyy-MM-dd)")] string? toDate = null,
        [Description("Max matches to return (default 20)")] int limit = 20,
        [Description("If true, return most recent matches first")] bool mostRecentFirst = false)
    {
        var from = ParseDate(fromDate);
        var to = ParseDate(toDate);
        if (fromDate is not null && from is null) return $"Invalid from_date '{fromDate}'. Use yyyy-MM-dd.";
        if (toDate is not null && to is null) return $"Invalid to_date '{toDate}'. Use yyyy-MM-dd.";

        var matches = _engine.FindMatches(team, opponent, competition, season, from, to, limit, mostRecentFirst);
        if (matches.Count == 0) return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"{Describe(team, opponent, competition, season)} — showing {matches.Count} match(es):");
        foreach (var m in matches) sb.AppendLine(FormatMatch(m));
        return sb.ToString();
    }

    [McpServerTool(Name = "head_to_head")]
    [Description("Compare two teams head-to-head: wins, draws, goals and the list of their matches, most recent first.")]
    public string HeadToHead(
        [Description("First team, e.g. 'Palmeiras'")] string teamA,
        [Description("Second team, e.g. 'Santos'")] string teamB,
        [Description("Max matches to list (default 10)")] int limit = 10)
    {
        var h2h = _engine.HeadToHead(teamA, teamB);
        if (h2h is null) return $"Could not resolve one of the teams: '{teamA}', '{teamB}'.";
        if (h2h.Matches.Count == 0) return $"No matches between {h2h.TeamA} and {h2h.TeamB} in the dataset.";

        var sb = new StringBuilder();
        sb.AppendLine($"{h2h.TeamA} vs {h2h.TeamB} — {h2h.Matches.Count} match(es) in dataset:");
        foreach (var m in h2h.Matches.Take(limit)) sb.AppendLine(FormatMatch(m));
        if (h2h.Matches.Count > limit) sb.AppendLine($"... ({h2h.Matches.Count - limit} more matches)");
        sb.AppendLine();
        sb.AppendLine($"Head-to-head: {h2h.TeamA} {h2h.WinsA} wins, {h2h.TeamB} {h2h.WinsB} wins, {h2h.Draws} draws. " +
                      $"Goals: {h2h.GoalsA}-{h2h.GoalsB}.");
        return sb.ToString();
    }

    [McpServerTool(Name = "team_statistics")]
    [Description("Win/draw/loss record and goals for a team, filterable by competition, season and venue (home/away/all).")]
    public string TeamStatistics(
        [Description("Team name, e.g. 'Corinthians'")] string team,
        [Description("Competition filter, e.g. 'Serie A'")] string? competition = null,
        [Description("Season filter, e.g. 2022")] int? season = null,
        [Description("'home', 'away' or 'all' (default)")] string venue = "all")
    {
        var r = _engine.TeamStatistics(team, competition, season, venue);
        if (r is null) return $"Team '{team}' not found in the dataset.";
        if (r.Played == 0) return $"No matches found for {team} with the given filters.";

        var sb = new StringBuilder();
        sb.AppendLine($"{_engine.ResolveTeam(team).DisplayName} record" +
                      $"{(competition is null ? "" : $" ({competition}")}{(season is null ? "" : $" {season}")}{(competition is null && season is null ? "" : ")")}, venue={venue}:");
        sb.AppendLine($"- Matches: {r.Played}");
        sb.AppendLine($"- Wins: {r.Wins}, Draws: {r.Draws}, Losses: {r.Losses}");
        sb.AppendLine($"- Goals For: {r.GoalsFor}, Goals Against: {r.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {r.WinRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool(Name = "competition_standings")]
    [Description("League standings for a competition season, calculated from match results (3 pts win, tie-break: wins, goal difference, goals for).")]
    public string CompetitionStandings(
        [Description("Competition, e.g. 'Brasileirão Série A' or 'Serie B'")] string competition,
        [Description("Season year, e.g. 2019")] int season,
        [Description("Rows to show (default 20)")] int limit = 20)
    {
        var table = _engine.Standings(competition, season);
        if (table is null || table.Count == 0)
            return $"No data for {competition} {season}. Available: use list_competitions / list_seasons.";

        var comp = Competitions.Normalize(competition) ?? competition;
        var sb = new StringBuilder();
        sb.AppendLine($"{comp} {season} standings (calculated from {table.Count} teams' matches):");
        var pos = 1;
        foreach (var (team, r) in table.Take(limit))
        {
            var note = pos == 1 ? " - Champion" : (comp.Contains("Série A") && pos > table.Count - 4 ? " - Relegated" : "");
            sb.AppendLine($"{pos,2}. {team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L) " +
                          $"GF {r.GoalsFor}, GA {r.GoalsAgainst}{note}");
            pos++;
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "search_players")]
    [Description("Search FIFA players by name, nationality, club and/or position (e.g. 'forward', 'GK', 'CM'), sorted by overall rating.")]
    public string SearchPlayers(
        [Description("Player name (partial ok), e.g. 'Gabriel Barbosa'")] string? name = null,
        [Description("Nationality, e.g. 'Brazil'")] string? nationality = null,
        [Description("Club name, e.g. 'Flamengo'")] string? club = null,
        [Description("Position code or group: GK/defender/midfielder/forward or e.g. 'LW'")] string? position = null,
        [Description("Minimum overall rating (0-99)")] int? minOverall = null,
        [Description("Max players to return (default 20)")] int limit = 20)
    {
        var players = _engine.SearchPlayers(name, nationality, club, position, minOverall, limit);
        if (players.Count == 0) return "No players found for the given criteria.";
        var sb = new StringBuilder();
        sb.AppendLine($"{players.Count} player(s) found (sorted by overall):");
        var rank = 1;
        foreach (var p in players) sb.AppendLine($"{rank++}. {FormatPlayer(p)}");
        return sb.ToString();
    }

    [McpServerTool(Name = "top_players")]
    [Description("Highest-rated FIFA players, optionally filtered by nationality (e.g. 'Brazil') and/or club (e.g. 'Flamengo').")]
    public string TopPlayers(
        [Description("Nationality filter, e.g. 'Brazil'")] string? nationality = null,
        [Description("Club filter, e.g. 'Flamengo'")] string? club = null,
        [Description("Max players to return (default 10)")] int limit = 10)
    {
        var players = _engine.TopPlayers(nationality, club, limit);
        if (players.Count == 0) return "No players found for the given criteria.";
        var sb = new StringBuilder();
        sb.AppendLine($"Top-rated players{(nationality is null ? "" : $" from {nationality}")}{(club is null ? "" : $" at {club}")}:");
        var rank = 1;
        foreach (var p in players) sb.AppendLine($"{rank++}. {FormatPlayer(p)}");
        return sb.ToString();
    }

    [McpServerTool(Name = "brazilian_club_rosters")]
    [Description("FIFA players grouped by Brazilian club: club, player count, average rating.")]
    public string BrazilianClubRosters(
        [Description("Minimum players for a club to be listed (default 3)")] int minPlayers = 3)
    {
        var rosters = _engine.BrazilianClubRosters(minPlayers);
        if (rosters.Count == 0) return "No Brazilian club rosters found in the FIFA dataset.";
        var sb = new StringBuilder();
        sb.AppendLine("Brazilian clubs in the FIFA player dataset:");
        foreach (var (club, count, avg) in rosters)
            sb.AppendLine($"- {club}: {count} players (avg rating: {avg:F0})");
        return sb.ToString();
    }

    [McpServerTool(Name = "biggest_wins")]
    [Description("Biggest victories in the dataset by goal margin, optionally filtered by competition and season.")]
    public string BiggestWins(
        [Description("Competition filter")] string? competition = null,
        [Description("Season filter")] int? season = null,
        [Description("Max results (default 10)")] int limit = 10)
    {
        var wins = _engine.BiggestWins(competition, season, limit);
        if (wins.Count == 0) return "No matches found for the given criteria.";
        var sb = new StringBuilder();
        sb.AppendLine("Biggest victories in the dataset:");
        var rank = 1;
        foreach (var m in wins) sb.AppendLine($"{rank++}. {FormatMatch(m)} (margin {m.GoalMargin})");
        return sb.ToString();
    }

    [McpServerTool(Name = "competition_stats")]
    [Description("Aggregate statistics: average goals per match, home win/draw/away win rates for a competition and/or season.")]
    public string CompetitionStats(
        [Description("Competition filter (omit for all competitions)")] string? competition = null,
        [Description("Season filter (omit for all seasons)")] int? season = null)
    {
        var stats = _engine.CompetitionStats(competition, season);
        if (stats is null) return "No matches found for the given criteria.";
        var (count, avgGoals, homeRate, drawRate, awayRate) = stats.Value;
        var sb = new StringBuilder();
        sb.AppendLine($"Statistics for {(competition ?? "all competitions")}{(season is null ? "" : $" {season}")} ({count} matches):");
        sb.AppendLine($"- Average goals per match: {avgGoals:F2}");
        sb.AppendLine($"- Home win rate: {homeRate:F1}%");
        sb.AppendLine($"- Draw rate: {drawRate:F1}%");
        sb.AppendLine($"- Away win rate: {awayRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool(Name = "find_derbies")]
    [Description("Find matches between traditional Brazilian rivals (Fla-Flu, Gre-Nal, Derby Paulista, Clássico Mineiro, ...), optionally by season and/or competition.")]
    public string FindDerbies(
        [Description("Season filter, e.g. 2023")] int? season = null,
        [Description("Competition filter")] string? competition = null,
        [Description("Max results (default 30)")] int limit = 30)
    {
        var derbies = _engine.FindDerbies(season, competition, limit);
        if (derbies.Count == 0) return "No derby matches found for the given criteria.";
        var sb = new StringBuilder();
        sb.AppendLine($"Derby matches{(season is null ? "" : $" in {season}")} (most recent first):");
        foreach (var (name, m) in derbies) sb.AppendLine($"[{name}] {FormatMatch(m)}");
        return sb.ToString();
    }

    [McpServerTool(Name = "best_records")]
    [Description("Best home or away records in a competition season (win rates, points).")]
    public string BestRecords(
        [Description("Competition, e.g. 'Serie A'")] string competition,
        [Description("Season, e.g. 2023")] int season,
        [Description("'home' or 'away' (default 'home')")] string venue = "home",
        [Description("Rows to show (default 10)")] int limit = 10)
    {
        var records = _engine.BestRecords(competition, season, venue, limit);
        if (records.Count == 0) return $"No data for {competition} {season}.";
        var sb = new StringBuilder();
        sb.AppendLine($"Best {venue} records — {competition} {season}:");
        var rank = 1;
        foreach (var (team, r) in records)
            sb.AppendLine($"{rank++}. {team}: {r.Points} pts in {r.Played} {venue} games " +
                          $"({r.Wins}W, {r.Draws}D, {r.Losses}L), win rate {r.WinRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool(Name = "list_competitions")]
    [Description("List the competitions covered by the dataset with match counts.")]
    public string ListCompetitions()
    {
        var sb = new StringBuilder();
        sb.AppendLine("Competitions in the dataset:");
        foreach (var (comp, count) in _engine.CompetitionMatchCounts.OrderBy(kv => kv.Key))
            sb.AppendLine($"- {comp}: {count} matches");
        return sb.ToString();
    }

    [McpServerTool(Name = "list_seasons")]
    [Description("List seasons covered by the dataset, optionally for one competition.")]
    public string ListSeasons(
        [Description("Competition filter")] string? competition = null)
    {
        IEnumerable<int> seasons = _engine.Seasons;
        if (competition is not null)
        {
            var comp = Competitions.Normalize(competition) ?? competition;
            seasons = _engine.FindMatches(competition: comp, limit: int.MaxValue)
                .Select(m => m.Season).Distinct().OrderBy(s => s);
        }
        var list = seasons.ToList();
        return list.Count == 0
            ? "No seasons found."
            : $"Seasons ({list.Min()}-{list.Max()}): {string.Join(", ", list)}";
    }

    // ---- formatting helpers ----

    private static string FormatMatch(MatchRecord m)
    {
        var home = TeamNameNormalizer.DisplayFor(m.HomeTeamKey);
        var away = TeamNameNormalizer.DisplayFor(m.AwayTeamKey);
        var round = string.IsNullOrWhiteSpace(m.Round) ? "" : $", round {m.Round}";
        return $"- {m.Date:yyyy-MM-dd}: {home} {m.HomeGoals}-{m.AwayGoals} {away} ({m.Competition}{round})";
    }

    private static string FormatPlayer(PlayerRecord p)
    {
        var parts = new List<string> { $"Overall: {p.Overall}" };
        if (p.Position is not null) parts.Add($"Position: {p.Position}");
        if (p.Club is not null) parts.Add($"Club: {p.Club}");
        if (p.Nationality is not null) parts.Add($"Nationality: {p.Nationality}");
        if (p.Age > 0) parts.Add($"Age: {p.Age}");
        return $"{p.Name} - {string.Join(", ", parts)}";
    }

    private static string Describe(string? team, string? opponent, string? competition, int? season)
    {
        var sb = new StringBuilder("Matches");
        if (team is not null) sb.Append($" for {team}");
        if (opponent is not null) sb.Append($" vs {opponent}");
        if (competition is not null) sb.Append($" in {competition}");
        if (season is not null) sb.Append($" {season}");
        return sb.ToString();
    }

    private static DateOnly? ParseDate(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null
        : DateOnly.TryParseExact(s.Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d) ? d
        : null;
}
