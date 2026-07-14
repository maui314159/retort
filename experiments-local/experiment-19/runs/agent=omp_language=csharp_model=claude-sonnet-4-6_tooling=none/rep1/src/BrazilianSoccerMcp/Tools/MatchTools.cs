using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class MatchTools(DataRepository repo)
{
    // ─── search_matches ───────────────────────────────────────────────────────

    [McpServerTool(Name = "search_matches")]
    [Description(
        "Search for soccer matches across all datasets. " +
        "Filter by team, opponent, competition (Brasileirao / Copa do Brasil / Copa Libertadores), " +
        "season (year), or date range. Returns up to 'limit' results ordered by date (newest first).")]
    public string SearchMatches(
        [Description("Team name to find (home or away). Partial match allowed, e.g. 'Flamengo'.")]
        string? team = null,
        [Description("Opponent team name. Combine with 'team' to find head-to-head matches.")]
        string? opponent = null,
        [Description("Competition filter: 'Brasileirao', 'Copa do Brasil', or 'Copa Libertadores'.")]
        string? competition = null,
        [Description("Season (year), e.g. 2023.")]
        int? season = null,
        [Description("Start date filter in yyyy-MM-dd format.")]
        string? dateFrom = null,
        [Description("End date filter in yyyy-MM-dd format.")]
        string? dateTo = null,
        [Description("Maximum number of matches to return (default 20, max 100).")]
        int limit = 20)
    {
        limit = Math.Clamp(limit, 1, 100);

        DateTime? from = null, to = null;
        if (!string.IsNullOrWhiteSpace(dateFrom) &&
            DateTime.TryParse(dateFrom, out var df)) from = df;
        if (!string.IsNullOrWhiteSpace(dateTo) &&
            DateTime.TryParse(dateTo, out var dt)) to = dt;

        var matches = repo.FindMatches(team, opponent, competition, season, from, to)
                          .Take(limit)
                          .ToList();

        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {matches.Count} match(es):");
        sb.AppendLine();

        foreach (var m in matches)
        {
            var round = string.IsNullOrWhiteSpace(m.Round) ? "" : $" (Round {m.Round})";
            sb.AppendLine(
                $"- {m.Date:yyyy-MM-dd}  {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam}" +
                $"  [{m.Competition} {m.Season}{round}]");
        }

        return sb.ToString().TrimEnd();
    }

    // ─── head_to_head ─────────────────────────────────────────────────────────

    [McpServerTool(Name = "head_to_head")]
    [Description(
        "Returns all matches played between two specific teams and their head-to-head record. " +
        "Optionally filter by competition and/or season.")]
    public string HeadToHead(
        [Description("First team name (e.g. 'Flamengo').")]
        string team1,
        [Description("Second team name (e.g. 'Fluminense').")]
        string team2,
        [Description("Competition filter (optional).")]
        string? competition = null,
        [Description("Season filter (optional).")]
        int? season = null)
    {
        // Find all matches where both teams appear on either side
        var t1k = Services.TeamNameNormalizer.Normalize(team1);
        var t2k = Services.TeamNameNormalizer.Normalize(team2);

        var matches = repo.FindMatches(team1, competition: competition, season: season)
            .Where(m => Services.TeamNameNormalizer.Matches(t2k, m.HomeTeamKey)
                     || Services.TeamNameNormalizer.Matches(t2k, m.AwayTeamKey))
            .ToList();

        if (matches.Count == 0)
            return $"No head-to-head matches found between '{team1}' and '{team2}'.";

        int t1Wins = 0, t2Wins = 0, draws = 0;

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-head: {team1} vs {team2}");
        sb.AppendLine();

        foreach (var m in matches)
        {
            bool t1IsHome = Services.TeamNameNormalizer.Matches(t1k, m.HomeTeamKey);
            int t1Goals = t1IsHome ? m.HomeGoals : m.AwayGoals;
            int t2Goals = t1IsHome ? m.AwayGoals : m.HomeGoals;

            if      (t1Goals > t2Goals) t1Wins++;
            else if (t1Goals < t2Goals) t2Wins++;
            else                        draws++;

            var round = string.IsNullOrWhiteSpace(m.Round) ? "" : $" Round {m.Round}";
            sb.AppendLine(
                $"- {m.Date:yyyy-MM-dd}  {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam}" +
                $"  [{m.Competition} {m.Season}{round}]");
        }

        sb.AppendLine();
        sb.AppendLine($"Summary: {team1} {t1Wins} wins, {team2} {t2Wins} wins, {draws} draws " +
                      $"({matches.Count} total matches)");

        return sb.ToString().TrimEnd();
    }

    // ─── get_team_stats ───────────────────────────────────────────────────────

    [McpServerTool(Name = "get_team_stats")]
    [Description(
        "Returns win/loss/draw record, goals scored/conceded, and points for a team. " +
        "Optionally filter by competition and/or season.")]
    public string GetTeamStats(
        [Description("Team name (e.g. 'Corinthians').")]
        string team,
        [Description("Competition filter (optional).")]
        string? competition = null,
        [Description("Season filter (optional).")]
        int? season = null,
        [Description("If true, also show separate home and away breakdowns.")]
        bool breakdown = false)
    {
        var overall = repo.GetTeamStats(team, competition, season);
        if (overall.Matches == 0)
            return $"No match data found for '{team}'.";

        var sb = new StringBuilder();
        var header = competition ?? "All competitions";
        if (season.HasValue) header += $" {season}";
        sb.AppendLine($"{team} — {header}");
        AppendStats(sb, "Overall", overall);

        if (breakdown)
        {
            var home = repo.GetHomeStats(team, competition, season);
            var away = repo.GetAwayStats(team, competition, season);
            AppendStats(sb, "Home", home);
            AppendStats(sb, "Away", away);
        }

        return sb.ToString().TrimEnd();

        static void AppendStats(StringBuilder sb, string label, DataRepository.TeamStats s)
        {
            var gd = s.GoalDifference >= 0 ? $"+{s.GoalDifference}" : $"{s.GoalDifference}";
            sb.AppendLine($"  {label}: {s.Matches} played — " +
                          $"{s.Wins}W {s.Draws}D {s.Losses}L — " +
                          $"GF {s.GoalsFor} GA {s.GoalsAgainst} GD {gd} — " +
                          $"{s.Points} pts — Win rate {s.WinRate:F1}%");
        }
    }

    // ─── get_standings ────────────────────────────────────────────────────────

    [McpServerTool(Name = "get_standings")]
    [Description(
        "Calculates and returns a league table (standings) for a given season, " +
        "derived from match results. Default competition is Brasileirao.")]
    public string GetStandings(
        [Description("Season year (e.g. 2019).")]
        int season,
        [Description("Competition: 'Brasileirao' (default) or 'Copa do Brasil'.")]
        string competition = "Brasileirao")
    {
        var rows = repo.GetStandings(season, competition);
        if (rows.Count == 0)
            return $"No standings data found for {competition} {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} Standings (calculated from match results):");
        sb.AppendLine();
        sb.AppendLine($"{"Pos",-4} {"Team",-30} {"P",3} {"W",3} {"D",3} {"L",3} " +
                      $"{"GF",4} {"GA",4} {"GD",4} {"Pts",4}");
        sb.AppendLine(new string('-', 65));

        foreach (var r in rows)
        {
            var gd = r.GoalDifference >= 0 ? $"+{r.GoalDifference}" : $"{r.GoalDifference}";
            sb.AppendLine(
                $"{r.Rank,-4} {r.Team,-30} {r.Played,3} {r.Wins,3} {r.Draws,3} {r.Losses,3} " +
                $"{r.GoalsFor,4} {r.GoalsAgainst,4} {gd,4} {r.Points,4}");
        }

        return sb.ToString().TrimEnd();
    }

    // ─── get_competition_stats ────────────────────────────────────────────────

    [McpServerTool(Name = "get_competition_stats")]
    [Description(
        "Returns aggregated statistics for a competition and/or season: " +
        "total matches, average goals per game, home win rate, and top scoring teams.")]
    public string GetCompetitionStats(
        [Description("Competition filter (optional).")]
        string? competition = null,
        [Description("Season filter (optional).")]
        int? season = null)
    {
        var matches = repo.FindMatches(competition: competition, season: season).ToList();
        if (matches.Count == 0)
            return "No data found for the given criteria.";

        var avg    = repo.AverageGoalsPerMatch(competition, season);
        var hwRate = repo.HomeWinRate(competition, season);
        var draws  = matches.Count(m => m.IsDraw);
        var awayW  = matches.Count(m => m.IsAwayWin);
        var topTeams = repo.TopScoringTeams(competition, season, 5).ToList();

        var sb = new StringBuilder();
        var label = competition ?? "All competitions";
        if (season.HasValue) label += $" {season}";
        sb.AppendLine($"Statistics — {label}");
        sb.AppendLine();
        sb.AppendLine($"Total matches  : {matches.Count}");
        sb.AppendLine($"Avg goals/match: {avg:F2}");
        sb.AppendLine($"Home win rate  : {hwRate:F1}%");
        sb.AppendLine($"Away win rate  : {(double)awayW / matches.Count * 100:F1}%");
        sb.AppendLine($"Draw rate      : {(double)draws / matches.Count * 100:F1}%");
        sb.AppendLine();
        sb.AppendLine("Top scoring teams:");
        int rank = 1;
        foreach (var (tm, goals, cnt) in topTeams)
            sb.AppendLine($"  {rank++}. {tm} — {goals} goals in {cnt} matches ({(double)goals / cnt:F2}/match)");

        return sb.ToString().TrimEnd();
    }

    // ─── get_biggest_wins ─────────────────────────────────────────────────────

    [McpServerTool(Name = "get_biggest_wins")]
    [Description(
        "Returns the matches with the largest goal margin in the dataset. " +
        "Optionally filter by competition and/or season.")]
    public string GetBiggestWins(
        [Description("Competition filter (optional).")]
        string? competition = null,
        [Description("Season filter (optional).")]
        int? season = null,
        [Description("Number of results to return (default 10).")]
        int limit = 10)
    {
        limit = Math.Clamp(limit, 1, 50);
        var wins = repo.BiggestWins(competition, season, limit).ToList();

        if (wins.Count == 0)
            return "No match data found.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest wins (by goal margin):");
        sb.AppendLine();
        int rank = 1;
        foreach (var m in wins)
        {
            sb.AppendLine(
                $"{rank++,2}. {m.Date:yyyy-MM-dd}  {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam}" +
                $"  (diff: {m.GoalDifference})  [{m.Competition} {m.Season}]");
        }
        return sb.ToString().TrimEnd();
    }

    // ─── get_best_home_record ─────────────────────────────────────────────────

    [McpServerTool(Name = "get_best_records")]
    [Description(
        "Returns teams with the best home or away records (win rate) in the dataset. " +
        "Requires at least 'minGames' matches to qualify.")]
    public string GetBestRecords(
        [Description("'home' or 'away' (default 'home').")]
        string homeOrAway = "home",
        [Description("Competition filter (optional).")]
        string? competition = null,
        [Description("Season filter (optional).")]
        int? season = null,
        [Description("Number of results (default 10).")]
        int limit = 10,
        [Description("Minimum matches played to qualify (default 5).")]
        int minGames = 5)
    {
        limit = Math.Clamp(limit, 1, 50);
        bool isHome = !homeOrAway.StartsWith("away", StringComparison.OrdinalIgnoreCase);

        var records = isHome
            ? repo.BestHomeRecords(competition, season, limit, minGames).ToList()
            : repo.BestAwayRecords(competition, season, limit, minGames).ToList();

        if (records.Count == 0)
            return $"No {homeOrAway} records found (min {minGames} games required).";

        var label = competition ?? "All competitions";
        if (season.HasValue) label += $" {season}";

        var sb = new StringBuilder();
        sb.AppendLine($"Best {homeOrAway} records — {label}:");
        sb.AppendLine();
        int rank = 1;
        foreach (var (tm, wr, played) in records)
            sb.AppendLine($"{rank++,2}. {tm,-30} Win rate: {wr:F1}%  ({played} games)");

        return sb.ToString().TrimEnd();
    }
}
