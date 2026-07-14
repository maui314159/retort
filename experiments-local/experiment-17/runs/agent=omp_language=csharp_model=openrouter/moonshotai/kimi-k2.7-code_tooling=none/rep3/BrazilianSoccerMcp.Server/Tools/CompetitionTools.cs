using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server.Tools;

[McpServerToolType]
public sealed class CompetitionTools
{
    private readonly CompetitionService _competitionService;

    public CompetitionTools(SoccerDataContext context)
    {
        _competitionService = new CompetitionService(context);
    }

    [McpServerTool]
    [Description("Calculate league standings for a competition and season using match results.")]
    public string GetStandings(
        [Description("Competition name, e.g. Brasileirão")] string competition,
        [Description("Season year")] int season)
    {
        var standings = _competitionService.GetStandings(competition, season);
        return _competitionService.FormatStandings(competition, season, standings);
    }

    [McpServerTool]
    [Description("Show tournament bracket / stage matches for a competition and season.")]
    public string GetBracket(
        [Description("Competition name, e.g. Copa Libertadores")] string competition,
        [Description("Season year")] int season,
        [Description("Stage, e.g. final, semifinals, quarterfinals, round of 16")] string stage)
    {
        var matches = _competitionService.GetBracket(competition, season, stage);
        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} {stage} matches:");

        if (matches.Count == 0)
        {
            sb.AppendLine("No matches found.");
            return sb.ToString();
        }

        foreach (var m in matches)
        {
            var date = m.Date?.ToString("yyyy-MM-dd") ?? "Unknown date";
            var detail = string.IsNullOrWhiteSpace(m.Round) ? stage : $"Round {m.Round}";
            sb.AppendLine($"- {date}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({detail})");
        }

        return sb.ToString();
    }
}
