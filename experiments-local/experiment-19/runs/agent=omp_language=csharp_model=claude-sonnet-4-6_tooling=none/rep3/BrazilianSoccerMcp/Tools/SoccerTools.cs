using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// All MCP tools for querying the Brazilian soccer knowledge graph.
/// The class is resolved from DI, so <see cref="DataRepository"/> is
/// constructor-injected.
/// </summary>
[McpServerToolType]
public class SoccerTools(DataRepository repo)
{
    // -----------------------------------------------------------------------
    // 1. Match search
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "search_matches")]
    [Description(
        "Search for Brazilian soccer matches. " +
        "Filter by team name, opponent (for head-to-head), competition, season, or date range. " +
        "Returns up to 'maxResults' matches sorted by date descending. " +
        "Team names are matched flexibly (partial, case-insensitive, state suffix ignored). " +
        "Competitions: 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores', 'Brasileirão Histórico', or any tournament name from BR-Football-Dataset.")]
    public string SearchMatches(
        [Description("Team name to search for, e.g. 'Flamengo', 'Palmeiras', 'Corinthians'")]
        string? team = null,

        [Description("Second team name for a head-to-head search, e.g. 'Fluminense'")]
        string? opponent = null,

        [Description("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores', 'Brasileirão Histórico', or a partial name")]
        string? competition = null,

        [Description("Season year, e.g. 2023")]
        int? season = null,

        [Description("Start date filter in YYYY-MM-DD format")]
        string? dateFrom = null,

        [Description("End date filter in YYYY-MM-DD format")]
        string? dateTo = null,

        [Description("Maximum number of matches to return (default 20, max 100)")]
        int maxResults = 20)
    {
        maxResults = Math.Clamp(maxResults, 1, 100);

        DateTime? from = TryParseDate(dateFrom);
        DateTime? to = TryParseDate(dateTo);

        var matches = repo.SearchMatches(team, opponent, competition, season, from, to, maxResults);

        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();

        // Head-to-head summary
        if (!string.IsNullOrWhiteSpace(team) && !string.IsNullOrWhiteSpace(opponent))
        {
            var (t1w, t2w, draws, total) = repo.GetHeadToHead(team, opponent, competition, season);
            var t1Name = DataRepository.NormalizeTeam(team);
            var t2Name = DataRepository.NormalizeTeam(opponent);
            sb.AppendLine($"Head-to-head ({t1Name} vs {t2Name}):");
            sb.AppendLine($"  Total: {total} matches | {t1Name} {t1w} – {draws} draws – {t2w} {t2Name}");
            sb.AppendLine();
        }

        sb.AppendLine($"Matches ({matches.Count} shown):");
        foreach (var m in matches)
        {
            var home = DataRepository.NormalizeTeam(m.HomeTeam);
            var away = DataRepository.NormalizeTeam(m.AwayTeam);
            var dateStr = m.Date.ToString("yyyy-MM-dd");
            var scoreStr = $"{home} {m.HomeGoals}-{m.AwayGoals} {away}";
            var detail = m.Stage is not null ? $" [{m.Stage}]"
                       : m.Round is not null ? $" [Round {m.Round}]"
                       : string.Empty;
            sb.AppendLine($"  {dateStr}: {scoreStr} ({m.Competition}{detail})");
        }

        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 2. Team statistics
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "get_team_stats")]
    [Description(
        "Get win/loss/draw statistics for a team. " +
        "Optionally filter by competition and/or season. " +
        "Set homeOnly=true to get only home match statistics.")]
    public string GetTeamStats(
        [Description("Team name, e.g. 'Corinthians', 'Flamengo'")]
        string team,

        [Description("Competition filter (optional)")]
        string? competition = null,

        [Description("Season year filter (optional)")]
        int? season = null,

        [Description("If true, only count home matches")]
        bool homeOnly = false)
    {
        var stats = repo.GetTeamStats(team, competition, season, homeOnly);

        if (stats.Played == 0)
            return $"No matches found for '{team}'" +
                   (competition != null ? $" in {competition}" : "") +
                   (season != null ? $" season {season}" : "") + ".";

        var sb = new StringBuilder();
        var t = DataRepository.NormalizeTeam(team);
        sb.AppendLine($"{t} statistics" +
                      (competition != null ? $" – {competition}" : "") +
                      (season != null ? $" {season}" : "") +
                      (homeOnly ? " (home only)" : "") + ":");
        sb.AppendLine($"  Matches: {stats.Played}");
        sb.AppendLine($"  Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"  Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}, GD: {stats.GoalDifference:+0;-#}");
        sb.AppendLine($"  Win rate: {stats.WinRate}%");
        sb.AppendLine($"  Points (3W+1D): {stats.Wins * 3 + stats.Draws}");
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 3. League standings
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "get_standings")]
    [Description(
        "Calculate league standings for a competition and season from match results. " +
        "Best supported for Brasileirão (seasons 2003-2023). " +
        "Use competition='Brasileirão' or 'Brasileirão Histórico' or 'Copa Libertadores'.")]
    public string GetStandings(
        [Description("Competition name, e.g. 'Brasileirão', 'Copa Libertadores'")]
        string competition,

        [Description("Season year, e.g. 2019")]
        int season,

        [Description("Number of teams to show (default 20)")]
        int topN = 20)
    {
        var standings = repo.GetStandings(competition, season, topN);

        if (standings.Count == 0)
            return $"No data found for {competition} {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} – Top {standings.Count} standings:");
        sb.AppendLine($"{"Pos",-4} {"Team",-30} {"P",3} {"W",3} {"D",3} {"L",3} {"GF",4} {"GA",4} {"GD",5} {"Pts",4}");
        sb.AppendLine(new string('-', 64));
        foreach (var s in standings)
        {
            var gd = s.GoalDifference >= 0 ? $"+{s.GoalDifference}" : s.GoalDifference.ToString();
            sb.AppendLine($"{s.Rank,-4} {s.Team,-30} {s.Played,3} {s.Wins,3} {s.Draws,3} {s.Losses,3} {s.GoalsFor,4} {s.GoalsAgainst,4} {gd,5} {s.Points,4}");
        }
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 4. Player search
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "search_players")]
    [Description(
        "Search the FIFA player database (18,000+ players). " +
        "Filter by name, nationality, club, position (GK/CB/ST/LW/etc.), or minimum overall rating. " +
        "Results sorted by overall rating descending.")]
    public string SearchPlayers(
        [Description("Player name or partial name, e.g. 'Neymar', 'Gabriel'")]
        string? name = null,

        [Description("Nationality, e.g. 'Brazil', 'Argentina'")]
        string? nationality = null,

        [Description("Club name or partial, e.g. 'Flamengo', 'Barcelona'")]
        string? club = null,

        [Description("Position code or partial, e.g. 'ST', 'GK', 'CB', 'LW'")]
        string? position = null,

        [Description("Minimum FIFA overall rating, e.g. 80")]
        int? minOverall = null,

        [Description("Maximum number of results to return (default 20, max 50)")]
        int maxResults = 20)
    {
        maxResults = Math.Clamp(maxResults, 1, 50);

        var players = repo.SearchPlayers(name, nationality, club, position, minOverall, maxResults);

        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Players ({players.Count} found):");
        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"  {i + 1,2}. {p.Name} (Age: {p.Age}) — Overall: {p.Overall}, Potential: {p.Potential}, Pos: {p.Position}");
            sb.AppendLine($"      Club: {p.Club}, Nationality: {p.Nationality}");
        }
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 5. Biggest wins
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "get_biggest_wins")]
    [Description(
        "List the matches with the largest goal difference (biggest victories). " +
        "Optionally filter by competition and/or season.")]
    public string GetBiggestWins(
        [Description("Competition filter (optional)")]
        string? competition = null,

        [Description("Season filter (optional)")]
        int? season = null,

        [Description("Number of results (default 10)")]
        int count = 10)
    {
        count = Math.Clamp(count, 1, 50);
        var matches = repo.GetBiggestWins(competition, season, count);

        if (matches.Count == 0)
            return "No matches found.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest victories{(competition != null ? $" in {competition}" : "")}{(season != null ? $" {season}" : "")}:");
        for (int i = 0; i < matches.Count; i++)
        {
            var m = matches[i];
            var home = DataRepository.NormalizeTeam(m.HomeTeam);
            var away = DataRepository.NormalizeTeam(m.AwayTeam);
            sb.AppendLine($"  {i + 1,2}. {m.Date:yyyy-MM-dd}: {home} {m.HomeGoals}-{m.AwayGoals} {away} ({m.Competition})");
        }
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 6. Aggregate statistics
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "get_statistics")]
    [Description(
        "Get aggregate statistics: average goals per match, home/away/draw rates, total matches. " +
        "Optionally filter by competition and/or season.")]
    public string GetStatistics(
        [Description("Competition filter (optional)")]
        string? competition = null,

        [Description("Season filter (optional)")]
        int? season = null)
    {
        var (avgGoals, homeWin, awayWin, drawRate, total) =
            repo.GetAggregateStats(competition, season);

        if (total == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Statistics{(competition != null ? $" – {competition}" : "")}{(season != null ? $" {season}" : "")}:");
        sb.AppendLine($"  Total matches: {total:N0}");
        sb.AppendLine($"  Average goals per match: {avgGoals}");
        sb.AppendLine($"  Home win rate: {homeWin}%");
        sb.AppendLine($"  Away win rate: {awayWin}%");
        sb.AppendLine($"  Draw rate: {drawRate}%");
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 7. Best home record
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "get_best_home_records")]
    [Description(
        "List the teams with the best home win percentage (minimum 5 home matches). " +
        "Optionally filter by competition and/or season.")]
    public string GetBestHomeRecords(
        [Description("Competition filter (optional)")]
        string? competition = null,

        [Description("Season filter (optional)")]
        int? season = null,

        [Description("Number of teams to show (default 10)")]
        int topN = 10)
    {
        topN = Math.Clamp(topN, 1, 30);
        var records = repo.GetBestHomeRecords(competition, season, topN);

        if (records.Count == 0)
            return "No data found.";

        var sb = new StringBuilder();
        sb.AppendLine($"Best home records{(competition != null ? $" – {competition}" : "")}{(season != null ? $" {season}" : "")}:");
        for (int i = 0; i < records.Count; i++)
        {
            var r = records[i];
            sb.AppendLine($"  {i + 1,2}. {r.Team,-30} {r.Wins}/{r.Played} wins ({r.WinRate}%)");
        }
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // 8. Data summary / discovery
    // -----------------------------------------------------------------------

    [McpServerTool(Name = "list_competitions")]
    [Description("List all competitions/tournaments available in the loaded datasets.")]
    public string ListCompetitions()
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Available competitions ({repo.Competitions.Count}):");
        foreach (var c in repo.Competitions)
            sb.AppendLine($"  - {c}");
        return sb.ToString();
    }

    [McpServerTool(Name = "list_seasons")]
    [Description("List all seasons (years) available in the dataset, optionally filtered by competition.")]
    public string ListSeasons(
        [Description("Competition filter (optional)")]
        string? competition = null)
    {
        IEnumerable<int> seasons;
        if (!string.IsNullOrWhiteSpace(competition))
        {
            seasons = repo.Matches
                .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)
                            && m.Season.HasValue)
                .Select(m => m.Season!.Value)
                .Distinct()
                .OrderDescending();
        }
        else
        {
            seasons = repo.Seasons;
        }

        var list = seasons.ToList();
        if (list.Count == 0) return "No seasons found.";

        var sb = new StringBuilder();
        sb.AppendLine($"Available seasons{(competition != null ? $" in {competition}" : "")} ({list.Count}):");
        sb.AppendLine("  " + string.Join(", ", list));
        return sb.ToString();
    }

    [McpServerTool(Name = "get_dataset_summary")]
    [Description("Get a summary of all loaded datasets: total matches per competition, total players.")]
    public string GetDatasetSummary()
    {
        var sb = new StringBuilder();
        sb.AppendLine("Brazilian Soccer Dataset Summary");
        sb.AppendLine($"  Total matches loaded: {repo.Matches.Count:N0}");
        sb.AppendLine($"  Total players (FIFA): {repo.Players.Count:N0}");
        sb.AppendLine();
        sb.AppendLine("Matches by competition:");
        foreach (var grp in repo.Matches
            .GroupBy(m => m.Competition)
            .OrderByDescending(g => g.Count()))
        {
            var minYear = grp.Where(m => m.Season.HasValue).Min(m => m.Season);
            var maxYear = grp.Where(m => m.Season.HasValue).Max(m => m.Season);
            var yearRange = (minYear.HasValue && maxYear.HasValue)
                ? $" ({minYear}–{maxYear})" : string.Empty;
            sb.AppendLine($"  {grp.Key,-40} {grp.Count(),6:N0} matches{yearRange}");
        }
        return sb.ToString();
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private static DateTime? TryParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateTime.TryParse(s, out var d) ? d : null;
    }
}
