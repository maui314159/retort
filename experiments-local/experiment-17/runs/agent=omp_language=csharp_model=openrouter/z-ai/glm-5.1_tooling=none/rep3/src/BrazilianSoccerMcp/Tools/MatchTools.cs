using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class MatchTools
{
    private readonly MatchDataLoader _matchLoader;

    public MatchTools(MatchDataLoader matchLoader) => _matchLoader = matchLoader;

    [McpServerTool, Description(
        "Search for soccer matches by team, opponent, competition, season, or date range. " +
        "Returns formatted match results with dates, scores, and competition info.")]
    public string search_matches(
        [Description("Team name to search for (matches home or away). e.g. 'Flamengo', 'Palmeiras'")]
        string team,
        [Description("Opponent team name (optional). e.g. 'Fluminense'")]
        string? opponent = null,
        [Description("Competition filter. Options: 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores', or leave empty for all.")]
        string? competition = null,
        [Description("Season/year filter. e.g. 2023")]
        int? season = null,
        [Description("Start date filter (YYYY-MM-DD). Optional.")]
        string? date_from = null,
        [Description("End date filter (YYYY-MM-DD). Optional.")]
        string? date_to = null,
        [Description("Maximum number of results to return. Default 20.")]
        int limit = 20)
    {
        var matches = _matchLoader.Matches.AsEnumerable();

        // Filter by team
        matches = matches.Where(m =>
            TeamNameNormalizer.Matches(m.HomeTeam, team) ||
            TeamNameNormalizer.Matches(m.AwayTeam, team));

        // Filter by opponent
        if (!string.IsNullOrWhiteSpace(opponent))
        {
            matches = matches.Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, opponent) ||
                TeamNameNormalizer.Matches(m.AwayTeam, opponent));
        }

        // Filter by competition
        if (!string.IsNullOrWhiteSpace(competition))
        {
            matches = matches.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        // Filter by season
        if (season.HasValue)
        {
            matches = matches.Where(m => m.Season == season.Value);
        }

        // Filter by date range
        if (DateTime.TryParse(date_from, out var from))
        {
            matches = matches.Where(m => m.Date >= from);
        }
        if (DateTime.TryParse(date_to, out var to))
        {
            matches = matches.Where(m => m.Date <= to);
        }

        var results = matches.OrderByDescending(m => m.Date).Take(limit).ToList();

        if (results.Count == 0)
            return "No matches found matching the specified criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} match(es):");
        sb.AppendLine();

        foreach (var match in results)
        {
            var score = $"{match.HomeGoals}-{match.AwayGoals}";
            var winner = match.IsHomeWin ? match.HomeTeam :
                         match.IsAwayWin ? match.AwayTeam : "Draw";
            sb.AppendLine($"- {match.Date:yyyy-MM-dd}: {match.HomeTeam} {score} {match.AwayTeam} ({match.Competition}{(string.IsNullOrEmpty(match.Round) ? "" : $", Round {match.Round}")})");
        }

        // Head-to-head summary if both team and opponent specified
        if (!string.IsNullOrWhiteSpace(opponent))
        {
            var allH2H = _matchLoader.Matches.Where(m =>
                (TeamNameNormalizer.Matches(m.HomeTeam, team) && (TeamNameNormalizer.Matches(m.AwayTeam, opponent))) ||
                (TeamNameNormalizer.Matches(m.AwayTeam, team) && (TeamNameNormalizer.Matches(m.HomeTeam, opponent))));

            var teamNorm = TeamNameNormalizer.Normalize(team);
            var teamWins = allH2H.Count(m =>
                (TeamNameNormalizer.Matches(m.HomeTeam, team) && m.IsHomeWin) ||
                (TeamNameNormalizer.Matches(m.AwayTeam, team) && m.IsAwayWin));
            var oppWins = allH2H.Count(m =>
                (TeamNameNormalizer.Matches(m.HomeTeam, opponent) && m.IsHomeWin) ||
                (TeamNameNormalizer.Matches(m.AwayTeam, opponent) && m.IsAwayWin));
            var draws = allH2H.Count(m => m.IsDraw);

            sb.AppendLine();
            sb.AppendLine($"Head-to-head ({teamNorm} vs {TeamNameNormalizer.Normalize(opponent)}): " +
                         $"{teamNorm} {teamWins} wins, {TeamNameNormalizer.Normalize(opponent)} {oppWins} wins, {draws} draws " +
                         $"(of {allH2H.Count()} total matches)");
        }

        return sb.ToString();
    }
}
