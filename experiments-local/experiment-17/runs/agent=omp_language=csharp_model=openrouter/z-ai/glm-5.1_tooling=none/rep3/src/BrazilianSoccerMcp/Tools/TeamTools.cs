using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class TeamTools
{
    private readonly MatchDataLoader _matchLoader;

    public TeamTools(MatchDataLoader matchLoader) => _matchLoader = matchLoader;

    [McpServerTool, Description(
        "Get statistics for a soccer team. Returns wins, draws, losses, goals for/against, " +
        "win rate, and goals per match. Optionally filter by season and competition.")]
    public string get_team_stats(
        [Description("Team name. e.g. 'Flamengo', 'Palmeiras', 'Corinthians'")]
        string team,
        [Description("Season/year filter. Optional.")]
        int? season = null,
        [Description("Competition filter. Options: 'Brasileirão', 'Copa do Brasil', 'Copa Libertadores'. Optional.")]
        string? competition = null,
        [Description("Home/Away filter. Options: 'home', 'away', or empty for all.")]
        string? venue = null)
    {
        var teamNorm = TeamNameNormalizer.Normalize(team);
        var teamMatches = _matchLoader.Matches.Where(m =>
            TeamNameNormalizer.Matches(m.HomeTeam, team) ||
            TeamNameNormalizer.Matches(m.AwayTeam, team));

        if (season.HasValue)
            teamMatches = teamMatches.Where(m => m.Season == season.Value);

        if (!string.IsNullOrWhiteSpace(competition))
            teamMatches = teamMatches.Where(m =>
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        var matchList = teamMatches.ToList();
        if (matchList.Count == 0)
            return $"No matches found for team '{teamNorm}' with the specified filters.";

        int homeWins = 0, homeDraws = 0, homeLosses = 0, homeGoalsFor = 0, homeGoalsAgainst = 0;
        int awayWins = 0, awayDraws = 0, awayLosses = 0, awayGoalsFor = 0, awayGoalsAgainst = 0;

        foreach (var m in matchList)
        {
            bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, team);
            if (isHome)
            {
                homeGoalsFor += m.HomeGoals;
                homeGoalsAgainst += m.AwayGoals;
                if (m.IsHomeWin) homeWins++;
                else if (m.IsDraw) homeDraws++;
                else homeLosses++;
            }
            else
            {
                awayGoalsFor += m.AwayGoals;
                awayGoalsAgainst += m.HomeGoals;
                if (m.IsAwayWin) awayWins++;
                else if (m.IsDraw) awayDraws++;
                else awayLosses++;
            }
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Statistics for {teamNorm}:");
        if (season.HasValue) sb.AppendLine($"  Season: {season.Value}");
        if (!string.IsNullOrWhiteSpace(competition)) sb.AppendLine($"  Competition: {competition}");

        if (string.IsNullOrWhiteSpace(venue) || venue.Equals("all", StringComparison.OrdinalIgnoreCase))
        {
            var totalMatches = homeWins + homeDraws + homeLosses + awayWins + awayDraws + awayLosses;
            var totalWins = homeWins + awayWins;
            var totalDraws = homeDraws + awayDraws;
            var totalLosses = homeLosses + awayLosses;
            var totalGf = homeGoalsFor + awayGoalsFor;
            var totalGa = homeGoalsAgainst + awayGoalsAgainst;

            sb.AppendLine();
            sb.AppendLine($"  Overall: {totalMatches} matches");
            sb.AppendLine($"  Record: {totalWins}W, {totalDraws}D, {totalLosses}L");
            sb.AppendLine($"  Goals: {totalGf} for, {totalGa} against (diff: {totalGf - totalGa})");
            sb.AppendLine($"  Win rate: {(totalMatches > 0 ? Math.Round((double)totalWins / totalMatches * 100, 1) : 0)}%");
            sb.AppendLine($"  Goals per match: {(totalMatches > 0 ? Math.Round((double)totalGf / totalMatches, 2) : 0)}");
            sb.AppendLine();
            sb.AppendLine($"  Home: {homeWins}W, {homeDraws}D, {homeLosses}L ({homeGoalsFor} GF, {homeGoalsAgainst} GA)");
            sb.AppendLine($"  Away: {awayWins}W, {awayDraws}D, {awayLosses}L ({awayGoalsFor} GF, {awayGoalsAgainst} GA)");
        }
        else if (venue.Equals("home", StringComparison.OrdinalIgnoreCase))
        {
            var homeTotal = homeWins + homeDraws + homeLosses;
            sb.AppendLine();
            sb.AppendLine($"  Home: {homeTotal} matches");
            sb.AppendLine($"  Record: {homeWins}W, {homeDraws}D, {homeLosses}L");
            sb.AppendLine($"  Goals: {homeGoalsFor} for, {homeGoalsAgainst} against");
            sb.AppendLine($"  Win rate: {(homeTotal > 0 ? Math.Round((double)homeWins / homeTotal * 100, 1) : 0)}%");
        }
        else if (venue.Equals("away", StringComparison.OrdinalIgnoreCase))
        {
            var awayTotal = awayWins + awayDraws + awayLosses;
            sb.AppendLine();
            sb.AppendLine($"  Away: {awayTotal} matches");
            sb.AppendLine($"  Record: {awayWins}W, {awayDraws}D, {awayLosses}L");
            sb.AppendLine($"  Goals: {awayGoalsFor} for, {awayGoalsAgainst} against");
            sb.AppendLine($"  Win rate: {(awayTotal > 0 ? Math.Round((double)awayWins / awayTotal * 100, 1) : 0)}%");
        }

        return sb.ToString();
    }

    [McpServerTool, Description(
        "Compare two teams head-to-head. Returns match history, win/loss/draw records, " +
        "and goals comparison between the two teams.")]
    public string head_to_head(
        [Description("First team name. e.g. 'Flamengo'")]
        string team1,
        [Description("Second team name. e.g. 'Fluminense'")]
        string team2,
        [Description("Competition filter. Optional.")]
        string? competition = null)
    {
        var team1Norm = TeamNameNormalizer.Normalize(team1);
        var team2Norm = TeamNameNormalizer.Normalize(team2);

        var h2h = _matchLoader.Matches.Where(m =>
            (TeamNameNormalizer.Matches(m.HomeTeam, team1) && TeamNameNormalizer.Matches(m.AwayTeam, team2)) ||
            (TeamNameNormalizer.Matches(m.HomeTeam, team2) && TeamNameNormalizer.Matches(m.AwayTeam, team1)));

        if (!string.IsNullOrWhiteSpace(competition))
            h2h = h2h.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        var matches = h2h.OrderByDescending(m => m.Date).ToList();

        if (matches.Count == 0)
            return $"No head-to-head matches found between {team1Norm} and {team2Norm}.";

        int t1Wins = 0, t2Wins = 0, draws = 0, t1Goals = 0, t2Goals = 0;

        foreach (var m in matches)
        {
            bool t1Home = TeamNameNormalizer.Matches(m.HomeTeam, team1);
            if (t1Home)
            {
                t1Goals += m.HomeGoals;
                t2Goals += m.AwayGoals;
                if (m.IsHomeWin) t1Wins++;
                else if (m.IsAwayWin) t2Wins++;
                else draws++;
            }
            else
            {
                t1Goals += m.AwayGoals;
                t2Goals += m.HomeGoals;
                if (m.IsAwayWin) t1Wins++;
                else if (m.IsHomeWin) t2Wins++;
                else draws++;
            }
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-head: {team1Norm} vs {team2Norm}");
        sb.AppendLine($"Total matches: {matches.Count}");
        sb.AppendLine($"{team1Norm}: {t1Wins} wins, {t1Goals} goals");
        sb.AppendLine($"{team2Norm}: {t2Wins} wins, {t2Goals} goals");
        sb.AppendLine($"Draws: {draws}");
        sb.AppendLine();

        // Show last 15 matches
        sb.AppendLine("Recent matches:");
        foreach (var m in matches.Take(15))
        {
            sb.AppendLine($"  {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition})");
        }

        if (matches.Count > 15)
            sb.AppendLine($"  ... and {matches.Count - 15} more");

        return sb.ToString();
    }
}
