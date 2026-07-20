using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class TeamTools
{
    private readonly DataService _data;

    public TeamTools(DataService data) => _data = data;

    private static bool CompetitionMatches(string competition, string filter)
    {
        var comparer = CultureInfo.InvariantCulture.CompareInfo;
        return comparer.IndexOf(competition, filter, CompareOptions.IgnoreCase | CompareOptions.IgnoreNonSpace) >= 0;
    }

    [McpServerTool]
    [Description("Get win/loss/draw statistics for a team in a given season and/or competition.")]
    public string GetTeamStats(
        [Description("Team name (e.g. 'Flamengo', 'Palmeiras', 'Corinthians').")] string team,
        [Description("Season year (e.g. 2023). If not specified, returns all-time stats.")] int? season = null,
        [Description("Competition filter (e.g. 'Brasileirao', 'Copa do Brasil'). Leave empty for all.")] string? competition = null,
        [Description("Include home vs away breakdown.")] bool homeAwayBreakdown = false)
    {
        var matches = _data.Matches
            .Where(m =>
                (TeamNameNormalizer.Matches(m.HomeTeam, team) || TeamNameNormalizer.Matches(m.AwayTeam, team))
                && m.HomeGoal.HasValue && m.AwayGoal.HasValue)
            .AsEnumerable();

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season);

        if (!string.IsNullOrWhiteSpace(competition))
            matches = matches.Where(m => CompetitionMatches(m.Competition, competition));

        var matchList = matches.ToList();

        if (matchList.Count == 0)
            return $"No match data found for '{team}'{(season.HasValue ? $" in {season}" : "")}.";

        int played = 0, wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
        int homePlayed = 0, homeWins = 0, homeDraws = 0, homeLosses = 0;
        int awayPlayed = 0, awayWins = 0, awayDraws = 0, awayLosses = 0;

        foreach (var m in matchList)
        {
            bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, team);
            int myGoals = isHome ? m.HomeGoal!.Value : m.AwayGoal!.Value;
            int oppGoals = isHome ? m.AwayGoal!.Value : m.HomeGoal!.Value;

            played++;
            goalsFor += myGoals;
            goalsAgainst += oppGoals;

            if (myGoals > oppGoals) { wins++; if (isHome) homeWins++; else awayWins++; }
            else if (myGoals < oppGoals) { losses++; if (isHome) homeLosses++; else awayLosses++; }
            else { draws++; if (isHome) homeDraws++; else awayDraws++; }

            if (isHome) homePlayed++;
            else awayPlayed++;
        }

        int points = wins * 3 + draws;
        double winRate = played > 0 ? (double)wins / played * 100 : 0;

        var sb = new StringBuilder();
        sb.AppendLine($"{team} Statistics{(season.HasValue ? $" ({season})" : " (all seasons)")}:");
        if (!string.IsNullOrWhiteSpace(competition)) sb.AppendLine($"Competition: {competition}");
        sb.AppendLine();
        sb.AppendLine($"Matches: {played} | Points: {points}");
        sb.AppendLine($"Wins: {wins} | Draws: {draws} | Losses: {losses}");
        sb.AppendLine($"Goals For: {goalsFor} | Goals Against: {goalsAgainst} | Goal Diff: {goalsFor - goalsAgainst}");
        sb.AppendLine($"Win Rate: {winRate:F1}%");

        if (homeAwayBreakdown)
        {
            sb.AppendLine();
            sb.AppendLine($"Home record ({homePlayed} matches): {homeWins}W {homeDraws}D {homeLosses}L");
            sb.AppendLine($"Away record ({awayPlayed} matches): {awayWins}W {awayDraws}D {awayLosses}L");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Compare two teams head-to-head statistics and overall performance side by side.")]
    public string CompareTeams(
        [Description("First team name.")] string team1,
        [Description("Second team name.")] string team2,
        [Description("Season year (optional).")] int? season = null)
    {
        var h2hMatches = _data.Matches
            .Where(m =>
                ((TeamNameNormalizer.Matches(m.HomeTeam, team1) && TeamNameNormalizer.Matches(m.AwayTeam, team2)) ||
                 (TeamNameNormalizer.Matches(m.HomeTeam, team2) && TeamNameNormalizer.Matches(m.AwayTeam, team1)))
                && m.HomeGoal.HasValue && m.AwayGoal.HasValue)
            .ToList();

        if (season.HasValue)
            h2hMatches = h2hMatches.Where(m => m.Season == season).ToList();

        int t1Wins = 0, t2Wins = 0, draws = 0;
        foreach (var m in h2hMatches)
        {
            bool t1IsHome = TeamNameNormalizer.Matches(m.HomeTeam, team1);
            int t1Goals = t1IsHome ? m.HomeGoal!.Value : m.AwayGoal!.Value;
            int t2Goals = t1IsHome ? m.AwayGoal!.Value : m.HomeGoal!.Value;
            if (t1Goals > t2Goals) t1Wins++;
            else if (t2Goals > t1Goals) t2Wins++;
            else draws++;
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Comparison: {team1} vs {team2}");
        sb.AppendLine();

        if (h2hMatches.Count > 0)
        {
            sb.AppendLine($"Head-to-Head ({h2hMatches.Count} matches):");
            sb.AppendLine($"  {team1}: {t1Wins} wins | {team2}: {t2Wins} wins | Draws: {draws}");
            sb.AppendLine();
        }

        foreach (var (teamName, label) in new[] { (team1, "Team 1"), (team2, "Team 2") })
        {
            var teamMatches = _data.Matches
                .Where(m =>
                    (TeamNameNormalizer.Matches(m.HomeTeam, teamName) || TeamNameNormalizer.Matches(m.AwayTeam, teamName))
                    && m.HomeGoal.HasValue && m.AwayGoal.HasValue
                    && (!season.HasValue || m.Season == season))
                .ToList();

            int wins = 0, d = 0, losses = 0, gf = 0, ga = 0;
            foreach (var m in teamMatches)
            {
                bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, teamName);
                int myG = isHome ? m.HomeGoal!.Value : m.AwayGoal!.Value;
                int oppG = isHome ? m.AwayGoal!.Value : m.HomeGoal!.Value;
                gf += myG; ga += oppG;
                if (myG > oppG) wins++;
                else if (myG < oppG) losses++;
                else d++;
            }

            sb.AppendLine($"{teamName} overall{(season.HasValue ? $" ({season})" : "")}:");
            sb.AppendLine($"  Matches: {teamMatches.Count} | W: {wins} D: {d} L: {losses} | GF: {gf} GA: {ga} GD: {gf - ga}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Find all competitions a team has participated in within the dataset.")]
    public string GetTeamCompetitions(
        [Description("Team name to look up.")] string team)
    {
        var teamMatches = _data.Matches
            .Where(m =>
                TeamNameNormalizer.Matches(m.HomeTeam, team) ||
                TeamNameNormalizer.Matches(m.AwayTeam, team))
            .ToList();

        if (teamMatches.Count == 0)
            return $"No matches found for team '{team}'.";

        var competitions = teamMatches
            .GroupBy(m => m.Competition)
            .Select(g => new { Competition = g.Key, Count = g.Count(), Seasons = g.Select(m => m.Season).Where(s => s.HasValue).Distinct().OrderBy(s => s).ToList() })
            .OrderByDescending(g => g.Count)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Competitions for {team} ({teamMatches.Count} total matches):");
        sb.AppendLine();

        foreach (var c in competitions)
        {
            var seasonsStr = c.Seasons.Count > 0 ? $" | Seasons: {string.Join(", ", c.Seasons)}" : "";
            sb.AppendLine($"- {c.Competition}: {c.Count} matches{seasonsStr}");
        }

        return sb.ToString();
    }
}
