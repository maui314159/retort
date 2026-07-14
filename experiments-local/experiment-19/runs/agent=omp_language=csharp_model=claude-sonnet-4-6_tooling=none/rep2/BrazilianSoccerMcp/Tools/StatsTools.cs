using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class StatsTools(DataRepository repo)
{
    [McpServerTool(Name = "get_team_statistics")]
    [Description(
        "Get win/draw/loss record, goals scored/conceded, and points for a team. " +
        "Optionally filter by season and competition.")]
    public string GetTeamStatistics(
        [Description("Team name (partial match). E.g. 'Flamengo', 'Corinthians'")] string team,
        [Description("Season year. E.g. 2023")] int? season = null,
        [Description("Competition: Brasileirao, CopaDoBrasil, Libertadores, BrFootball, HistoricoBrasileiro")] string? competition = null)
    {
        var comp = ParseCompetition(competition);
        var stats = repo.GetTeamStats(team, season, comp);

        if (stats.Matches == 0)
            return $"No matches found for '{team}'" +
                   (season.HasValue ? $" in {season}" : "") +
                   (competition != null ? $" ({competition})" : "") + ".";

        var sb = new StringBuilder();
        sb.AppendLine($"Statistics for {stats.Team}" +
            (season.HasValue ? $" — {season}" : "") +
            (competition != null ? $" — {competition}" : ""));
        sb.AppendLine();
        sb.AppendLine($"  Matches:  {stats.Matches}");
        sb.AppendLine($"  Record:   {stats.Wins}W / {stats.Draws}D / {stats.Losses}L");
        sb.AppendLine($"  Points:   {stats.Points}");
        sb.AppendLine($"  Goals:    {stats.GoalsFor} scored, {stats.GoalsAgainst} conceded (GD: {stats.GoalDifference:+#;-#;0})");
        sb.AppendLine($"  Win rate: {stats.WinRate:F1}%");

        return sb.ToString();
    }

    [McpServerTool(Name = "get_standings")]
    [Description(
        "Calculate league standings for a season from match results. " +
        "Returns ranked table with points, W/D/L, goals.")]
    public string GetStandings(
        [Description("Season year, e.g. 2023")] int season,
        [Description("Competition (default: Brasileirao). Options: Brasileirao, HistoricoBrasileiro")] string competition = "Brasileirao")
    {
        var comp = ParseCompetition(competition) ?? Competition.Brasileirao;
        var standings = repo.GetStandings(season, comp);

        if (standings.Count == 0)
            return $"No match data found for {season} {competition}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{season} {comp} Standings (calculated from match results):");
        sb.AppendLine();
        sb.AppendLine($"  {"Pos",-4} {"Team",-30} {"Pts",-5} {"MP",-4} {"W",-4} {"D",-4} {"L",-4} {"GF",-4} {"GA",-4} {"GD",-5}");
        sb.AppendLine(new string('-', 75));

        int pos = 1;
        foreach (var (stats, teamName) in standings)
        {
            var gd = stats.GoalDifference >= 0 ? $"+{stats.GoalDifference}" : $"{stats.GoalDifference}";
            sb.AppendLine(
                $"  {pos,-4} {teamName,-30} {stats.Points,-5} {stats.Matches,-4} {stats.Wins,-4} {stats.Draws,-4} {stats.Losses,-4} {stats.GoalsFor,-4} {stats.GoalsAgainst,-4} {gd,-5}");
            pos++;
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_biggest_wins")]
    [Description(
        "Get the biggest victories (by goal difference) in the dataset. " +
        "Optionally filter by competition.")]
    public string GetBiggestWins(
        [Description("Competition filter: Brasileirao, CopaDoBrasil, Libertadores, BrFootball, HistoricoBrasileiro")] string? competition = null,
        [Description("Number of results to return (default 10)")] int limit = 10)
    {
        var comp = ParseCompetition(competition);
        var matches = repo.GetBiggestWins(comp, limit);

        if (matches.Count == 0)
            return "No matches found.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest victories{(competition != null ? $" in {competition}" : "")} (by goal difference):");
        sb.AppendLine();

        int rank = 1;
        foreach (var m in matches)
        {
            var winner = m.HomeGoals > m.AwayGoals
                ? TeamNameNormalizer.Normalize(m.HomeTeam)
                : TeamNameNormalizer.Normalize(m.AwayTeam);
            sb.AppendLine(
                $"  {rank++,2}. {m.Date:yyyy-MM-dd}  {TeamNameNormalizer.Normalize(m.HomeTeam)} {m.HomeGoals}-{m.AwayGoals} {TeamNameNormalizer.Normalize(m.AwayTeam)}");
            sb.AppendLine($"      Winner by {m.GoalDifference} | {m.CompetitionLabel} {m.Season}" +
                (m.Stage != null ? $" | {m.Stage}" : ""));
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_competition_stats")]
    [Description(
        "Get aggregate statistics for a competition: average goals per match, " +
        "home/away/draw rates, total matches.")]
    public string GetCompetitionStats(
        [Description("Competition: Brasileirao, CopaDoBrasil, Libertadores, BrFootball, HistoricoBrasileiro. Leave null for all.")] string? competition = null,
        [Description("Season year filter. E.g. 2023")] int? season = null)
    {
        var comp = ParseCompetition(competition);
        var (avgGoals, homeWinRate, drawRate, awayWinRate, total) =
            repo.GetCompetitionStats(comp, season);

        if (total == 0)
            return "No data found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Competition statistics:" +
            (competition != null ? $" {competition}" : " (all competitions)") +
            (season.HasValue ? $" — {season}" : ""));
        sb.AppendLine();
        sb.AppendLine($"  Total matches:       {total}");
        sb.AppendLine($"  Avg goals per match: {avgGoals:F2}");
        sb.AppendLine($"  Home win rate:       {homeWinRate:F1}%");
        sb.AppendLine($"  Draw rate:           {drawRate:F1}%");
        sb.AppendLine($"  Away win rate:       {awayWinRate:F1}%");

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
}
