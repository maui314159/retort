using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class MatchTools(DataRepository repo)
{
    [McpServerTool(Name = "search_matches")]
    [Description(
        "Search for Brazilian soccer matches across all datasets (Brasileirão, Copa do Brasil, " +
        "Copa Libertadores). Filter by team, season, competition, or date range.")]
    public string SearchMatches(
        [Description("Team name to search for (partial match, accent-tolerant). E.g. 'Flamengo', 'Palmeiras'")] string? team = null,
        [Description("Opponent team name (finds head-to-head matches when combined with 'team')")] string? opponent = null,
        [Description("Season year, e.g. 2023")] int? season = null,
        [Description("Competition: Brasileirao, CopaDoBrasil, Libertadores, BrFootball, HistoricoBrasileiro")] string? competition = null,
        [Description("Start date in YYYY-MM-DD format")] string? fromDate = null,
        [Description("End date in YYYY-MM-DD format")] string? toDate = null,
        [Description("Maximum results to return (default 20)")] int limit = 20)
    {
        var comp = ParseCompetition(competition);
        var from = ParseDate(fromDate);
        var to = ParseDate(toDate);

        var matches = repo.SearchMatches(team, opponent, season, comp, from, to, limit);

        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {matches.Count} match(es):");
        sb.AppendLine();

        foreach (var m in matches)
        {
            sb.AppendLine($"  {m.Date:yyyy-MM-dd}  {TeamNameNormalizer.Normalize(m.HomeTeam)} {m.HomeGoals}-{m.AwayGoals} {TeamNameNormalizer.Normalize(m.AwayTeam)}");
            sb.AppendLine($"    Competition: {m.CompetitionLabel} | Season: {m.Season}" +
                (m.Round != null ? $" | Round: {m.Round}" : "") +
                (m.Stage != null ? $" | Stage: {m.Stage}" : ""));
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_head_to_head")]
    [Description(
        "Get head-to-head record between two teams including all matches and summary statistics.")]
    public string GetHeadToHead(
        [Description("First team name")] string team1,
        [Description("Second team name")] string team2,
        [Description("Optionally filter by season year")] int? season = null,
        [Description("Maximum number of matches to list (default 20)")] int limit = 20)
    {
        var matches = repo.SearchMatches(team: team1, opponent: team2, season: season, limit: limit);

        if (matches.Count == 0)
            return $"No head-to-head matches found between '{team1}' and '{team2}'.";

        int team1Wins = 0, team2Wins = 0, draws = 0;
        int team1Goals = 0, team2Goals = 0;

        foreach (var m in matches)
        {
            bool t1IsHome = TeamNameNormalizer.Matches(m.HomeTeam, team1);
            int t1g = t1IsHome ? m.HomeGoals : m.AwayGoals;
            int t2g = t1IsHome ? m.AwayGoals : m.HomeGoals;
            team1Goals += t1g;
            team2Goals += t2g;
            if (t1g > t2g) team1Wins++;
            else if (t1g < t2g) team2Wins++;
            else draws++;
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-Head: {team1} vs {team2}" + (season.HasValue ? $" ({season})" : ""));
        sb.AppendLine($"Record: {team1} {team1Wins}W | {draws}D | {team2Wins}W {team2}");
        sb.AppendLine($"Goals: {team1} {team1Goals} - {team2Goals} {team2}");
        sb.AppendLine();

        foreach (var m in matches)
        {
            var ht = TeamNameNormalizer.Normalize(m.HomeTeam);
            var at = TeamNameNormalizer.Normalize(m.AwayTeam);
            sb.AppendLine($"  {m.Date:yyyy-MM-dd}  {ht} {m.HomeGoals}-{m.AwayGoals} {at}  ({m.CompetitionLabel}" +
                (m.Round != null ? $" R{m.Round}" : "") + ")");
        }

        return sb.ToString();
    }

    private static Competition? ParseCompetition(string? s) => s?.ToLowerInvariant().Replace(" ", "") switch
    {
        "brasileirao" or "brasileirão" or "seriea" => Competition.Brasileirao,
        "copodobrasil" or "copa" or "cup" => Competition.CopaDoBrasil,
        "libertadores" or "copalibertadores" => Competition.Libertadores,
        "brfootball" => Competition.BrFootball,
        "historico" or "historicobrasileiro" or "historicobrasileirao" => Competition.HistoricoBrasileiro,
        null => null,
        _ => null,
    };

    private static DateOnly? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (DateOnly.TryParseExact(s.Trim(), "yyyy-MM-dd", null,
                System.Globalization.DateTimeStyles.None, out var d))
            return d;
        return null;
    }
}
