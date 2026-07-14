using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class CompetitionTools
{
    private readonly MatchDataLoader _matchLoader;

    public CompetitionTools(MatchDataLoader matchLoader) => _matchLoader = matchLoader;

    [McpServerTool, Description(
        "Get competition standings calculated from match results. " +
        "Returns a table with points, wins, draws, losses, and goals for each team.")]
    public string get_competition_standings(
        [Description("Competition name. Options: 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores'")]
        string competition,
        [Description("Season/year. e.g. 2023")]
        int season)
    {
        var matches = _matchLoader.Matches.Where(m =>
            m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) &&
            m.Season == season).ToList();

        if (matches.Count == 0)
            return $"No matches found for {competition} {season}.";

        var standings = new Dictionary<string, TeamStats>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            var homeNorm = TeamNameNormalizer.Normalize(m.HomeTeam);
            var awayNorm = TeamNameNormalizer.Normalize(m.AwayTeam);

            if (!standings.TryGetValue(homeNorm, out var homeStats))
                homeStats = new TeamStats { Team = homeNorm };
            if (!standings.TryGetValue(awayNorm, out var awayStats))
                awayStats = new TeamStats { Team = awayNorm };

            // Home team stats
            var newHome = new TeamStats
            {
                Team = homeNorm,
                Matches = 1,
                Wins = m.IsHomeWin ? 1 : 0,
                Draws = m.IsDraw ? 1 : 0,
                Losses = m.IsAwayWin ? 1 : 0,
                GoalsFor = m.HomeGoals,
                GoalsAgainst = m.AwayGoals,
            };
            standings[homeNorm] = homeStats + newHome;

            // Away team stats
            var newAway = new TeamStats
            {
                Team = awayNorm,
                Matches = 1,
                Wins = m.IsAwayWin ? 1 : 0,
                Draws = m.IsDraw ? 1 : 0,
                Losses = m.IsHomeWin ? 1 : 0,
                GoalsFor = m.AwayGoals,
                GoalsAgainst = m.HomeGoals,
            };
            standings[awayNorm] = awayStats + newAway;
        }

        var sorted = standings.Values
            .OrderByDescending(s => s.Points)
            .ThenByDescending(s => s.GoalsFor - s.GoalsAgainst)
            .ThenByDescending(s => s.GoalsFor)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} Standings (calculated from {matches.Count} matches):");
        sb.AppendLine();
        sb.AppendLine($"{"Pos",-4} {"Team",-25} {"Pts",-5} {"W",-4} {"D",-4} {"L",-4} {"GF",-4} {"GA",-4} {"GD",-5}");
        sb.AppendLine(new string('-', 60));

        for (int i = 0; i < sorted.Count; i++)
        {
            var s = sorted[i];
            var gd = s.GoalsFor - s.GoalsAgainst;
            var pos = i + 1;
            var marker = pos == 1 ? " ★ Champion" : "";
            var relegated = pos > sorted.Count - 4 ? " ↓ Relegated" : "";
            sb.AppendLine($"{pos,-4} {s.Team,-25} {s.Points,-5} {s.Wins,-4} {s.Draws,-4} {s.Losses,-4} {s.GoalsFor,-4} {s.GoalsAgainst,-4} {gd,-5}{marker}{relegated}");
        }

        return sb.ToString();
    }
}
