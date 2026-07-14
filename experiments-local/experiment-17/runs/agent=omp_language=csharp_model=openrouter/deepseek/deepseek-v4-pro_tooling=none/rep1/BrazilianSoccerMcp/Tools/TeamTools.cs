using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// MCP tools for team statistics and performance analysis.
/// </summary>
[McpServerToolType]
public static class TeamTools
{
    private static DataLoader Data => DataStore.Loader;

    [McpServerTool, Description("Get detailed statistics for a team: win/loss/draw records, goals for/against, home/away splits. Filter by season and/or competition.")]
    public static string GetTeamStats(
        [Description("Team name, e.g. 'Flamengo', 'Palmeiras'.")] string team,
        [Description("Optional season filter, e.g. 2023.")] int? season = null,
        [Description("Optional competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores'.")] string? competition = null)
    {
        var query = Data.Matches.AsEnumerable();

        query = query.Where(m =>
            TeamNormalizer.Matches(m.HomeTeam, team) ||
            TeamNormalizer.Matches(m.AwayTeam, team));

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        var matches = query.OrderBy(m => m.Date).ToList();

        if (matches.Count == 0)
            return $"No matches found for {team}" +
                   (season.HasValue ? $" in {season}" : "") +
                   (!string.IsNullOrWhiteSpace(competition) ? $" ({competition})" : "") + ".";

        int totalWins = 0, totalLosses = 0, totalDraws = 0;
        int goalsFor = 0, goalsAgainst = 0;
        int homeWins = 0, homeDraws = 0, homeLosses = 0;
        int awayWins = 0, awayDraws = 0, awayLosses = 0;
        int homeGoalsFor = 0, homeGoalsAgainst = 0;
        int awayGoalsFor = 0, awayGoalsAgainst = 0;

        var competitions = new Dictionary<string, int>();

        foreach (var m in matches)
        {
            bool isHome = TeamNormalizer.Matches(m.HomeTeam, team);
            int gf = isHome ? m.HomeGoals : m.AwayGoals;
            int ga = isHome ? m.AwayGoals : m.HomeGoals;

            goalsFor += gf;
            goalsAgainst += ga;

            if (gf > ga) { totalWins++; if (isHome) homeWins++; else awayWins++; }
            else if (gf < ga) { totalLosses++; if (isHome) homeLosses++; else awayLosses++; }
            else { totalDraws++; if (isHome) homeDraws++; else awayDraws++; }

            if (isHome) { homeGoalsFor += gf; homeGoalsAgainst += ga; }
            else { awayGoalsFor += gf; awayGoalsAgainst += ga; }

            var comp = m.Competition;
            competitions.TryGetValue(comp, out var c);
            competitions[comp] = c + 1;
        }

        var homeMatches = homeWins + homeDraws + homeLosses;
        var awayMatches = awayWins + awayDraws + awayLosses;

        var sb = new StringBuilder();
        sb.AppendLine($"{team} Statistics:");
        sb.AppendLine($"  Total matches: {matches.Count}");

        if (season.HasValue) sb.AppendLine($"  Season: {season}");
        sb.AppendLine($"  Wins: {totalWins}, Draws: {totalDraws}, Losses: {totalLosses}");
        sb.AppendLine($"  Goals For: {goalsFor}, Goals Against: {goalsAgainst} (Diff: {goalsFor - goalsAgainst:+0;-0})");
        sb.AppendLine($"  Win Rate: {(matches.Count > 0 ? (double)totalWins / matches.Count * 100 : 0):F1}%");
        sb.AppendLine();

        sb.AppendLine("Home Record:");
        sb.AppendLine($"  Matches: {homeMatches}, Wins: {homeWins}, Draws: {homeDraws}, Losses: {homeLosses}");
        sb.AppendLine($"  Goals For: {homeGoalsFor}, Against: {homeGoalsAgainst}");
        sb.AppendLine($"  Home Win Rate: {(homeMatches > 0 ? (double)homeWins / homeMatches * 100 : 0):F1}%");
        sb.AppendLine();

        sb.AppendLine("Away Record:");
        sb.AppendLine($"  Matches: {awayMatches}, Wins: {awayWins}, Draws: {awayDraws}, Losses: {awayLosses}");
        sb.AppendLine($"  Goals For: {awayGoalsFor}, Against: {awayGoalsAgainst}");
        sb.AppendLine($"  Away Win Rate: {(awayMatches > 0 ? (double)awayWins / awayMatches * 100 : 0):F1}%");
        sb.AppendLine();

        sb.AppendLine("Competitions played:");
        foreach (var kvp in competitions.OrderByDescending(k => k.Value))
            sb.AppendLine($"  {kvp.Key}: {kvp.Value} matches");

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Rank teams by a statistic across all data or filtered by season/competition. Choose metric: 'goals', 'wins', 'win_rate', 'points'.")]
    public static string RankTeams(
        [Description("Metric to rank by: 'goals' (goals scored), 'wins', 'win_rate', 'points' (3 per win, 1 per draw).")] string metric = "wins",
        [Description("Optional season filter.")] int? season = null,
        [Description("Optional competition filter.")] string? competition = null,
        [Description("Number of teams to show (default 10).")] int top = 10)
    {
        var query = Data.Matches.AsEnumerable();

        if (season.HasValue)
            query = query.Where(m => m.Season == season.Value);

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        var matches = query.ToList();

        var teamStats = new Dictionary<string, (int Wins, int Draws, int Losses, int GoalsFor, int GoalsAgainst)>();

        foreach (var m in matches)
        {
            void AddTeam(string teamName, bool isHome)
            {
                if (!teamStats.TryGetValue(teamName, out var st))
                    st = (0, 0, 0, 0, 0);

                int gf = isHome ? m.HomeGoals : m.AwayGoals;
                int ga = isHome ? m.AwayGoals : m.HomeGoals;

                if (gf > ga) st.Wins++;
                else if (gf < ga) st.Losses++;
                else st.Draws++;

                st.GoalsFor += gf;
                st.GoalsAgainst += ga;
                teamStats[teamName] = st;
            }

            AddTeam(m.HomeTeam, true);
            AddTeam(m.AwayTeam, false);
        }

        var ranked = teamStats
            .Select(kvp => new
            {
                Team = kvp.Key,
                kvp.Value.Wins,
                kvp.Value.Draws,
                kvp.Value.Losses,
                kvp.Value.GoalsFor,
                kvp.Value.GoalsAgainst,
                Points = kvp.Value.Wins * 3 + kvp.Value.Draws,
                WinRate = (kvp.Value.Wins + kvp.Value.Draws + kvp.Value.Losses) > 0
                    ? (double)kvp.Value.Wins / (kvp.Value.Wins + kvp.Value.Draws + kvp.Value.Losses) * 100
                    : 0
            });

        ranked = metric.ToLowerInvariant() switch
        {
            "goals" => ranked.OrderByDescending(r => r.GoalsFor),
            "win_rate" => ranked.OrderByDescending(r => r.WinRate),
            "points" => ranked.OrderByDescending(r => r.Points),
            _ => ranked.OrderByDescending(r => r.Wins),
        };

        var topTeams = ranked.Take(top).ToList();

        if (topTeams.Count == 0)
            return "No team data found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Top {topTeams.Count} teams by {metric}" +
                       (season.HasValue ? $" in {season}" : "") +
                       (!string.IsNullOrWhiteSpace(competition) ? $" ({competition})" : "") + ":");
        sb.AppendLine();

        for (int i = 0; i < topTeams.Count; i++)
        {
            var t = topTeams[i];
            sb.AppendLine($"  {i + 1}. {t.Team} - {t.Wins}W {t.Draws}D {t.Losses}L, GF:{t.GoalsFor} GA:{t.GoalsAgainst}, Pts:{t.Points}");
        }

        return sb.ToString().TrimEnd();
    }
}