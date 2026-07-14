using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// MCP tools for competition standings, champions, and tournament queries.
/// </summary>
[McpServerToolType]
public static class CompetitionTools
{
    private static DataLoader Data => DataStore.Loader;

    [McpServerTool, Description("Calculate league standings from match results. Returns table with points, wins, draws, losses, goals. Points system: 3 for win, 1 for draw.")]
    public static string GetStandings(
        [Description("Season year, e.g. 2023.")] int season,
        [Description("Competition: 'Brasileirão' (default), 'Copa do Brasil', 'Libertadores'.")] string competition = "Brasileirão")
    {
        var matches = Data.Matches
            .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) &&
                        m.Season == season)
            .ToList();

        if (matches.Count == 0)
            return $"No match data found for {competition} in {season}.";

        var teams = new Dictionary<string, (int Pts, int W, int D, int L, int GF, int GA, int GP)>();

        foreach (var m in matches)
        {
            if (!teams.ContainsKey(m.HomeTeam))
                teams[m.HomeTeam] = (0, 0, 0, 0, 0, 0, 0);
            if (!teams.ContainsKey(m.AwayTeam))
                teams[m.AwayTeam] = (0, 0, 0, 0, 0, 0, 0);

            var home = teams[m.HomeTeam];
            var away = teams[m.AwayTeam];

            home.GP++; away.GP++;
            home.GF += m.HomeGoals; home.GA += m.AwayGoals;
            away.GF += m.AwayGoals; away.GA += m.HomeGoals;

            if (m.HomeGoals > m.AwayGoals)
            {
                home.Pts += 3; home.W++;
                away.L++;
            }
            else if (m.HomeGoals < m.AwayGoals)
            {
                away.Pts += 3; away.W++;
                home.L++;
            }
            else
            {
                home.Pts++; away.Pts++;
                home.D++; away.D++;
            }

            teams[m.HomeTeam] = home;
            teams[m.AwayTeam] = away;
        }

        var standings = teams
            .Select(kvp => new { Team = kvp.Key, kvp.Value.Pts, kvp.Value.W, kvp.Value.D, kvp.Value.L, kvp.Value.GF, kvp.Value.GA, kvp.Value.GP, GD = kvp.Value.GF - kvp.Value.GA })
            .OrderByDescending(s => s.Pts)
            .ThenByDescending(s => s.GD)
            .ThenByDescending(s => s.GF)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} {season} - Final Standings (calculated from matches):");
        sb.AppendLine();
        sb.AppendLine($"{"#",-3} {"Team",-22} {"Pts",-4} {"GP",-3} {"W",-3} {"D",-3} {"L",-3} {"GF",-4} {"GA",-4} {"GD",-4}");
        sb.AppendLine(new string('-', 56));

        int pos = 1;
        foreach (var t in standings)
        {
            var prefix = pos switch { 1 => "C", <= 4 => "*", _ => " " };
            sb.AppendLine($"{pos,-3}{prefix}{t.Team,-21} {t.Pts,-4} {t.GP,-3} {t.W,-3} {t.D,-3} {t.L,-3} {t.GF,-4} {t.GA,-4} {t.GD,-4}");
            pos++;
        }

        // Add champion info
        var champion = standings.First();
        sb.AppendLine();
        sb.AppendLine($"Champion: {champion.Team} ({champion.Pts} points)");
        sb.AppendLine($"  Record: {champion.W}W {champion.D}D {champion.L}L, GF:{champion.GF} GA:{champion.GA} GD:{champion.GD}");

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("List all competition champions found in the dataset by season.")]
    public static string GetChampions(
        [Description("Competition: 'Brasileirão' (default), 'Copa do Brasil', 'Libertadores'.")] string competition = "Brasileirão")
    {
        var seasons = Data.Matches
            .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) && m.Season.HasValue)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();

        if (seasons.Count == 0)
            return $"No {competition} data found.";

        var sb = new StringBuilder();
        sb.AppendLine($"{competition} Champions by Season:");
        sb.AppendLine();

        foreach (var season in seasons)
        {
            var matches = Data.Matches
                .Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) &&
                            m.Season == season)
                .ToList();

            var teams = new Dictionary<string, (int Pts, int GD, int GF)>();

            foreach (var m in matches)
            {
                if (!teams.ContainsKey(m.HomeTeam)) teams[m.HomeTeam] = (0, 0, 0);
                if (!teams.ContainsKey(m.AwayTeam)) teams[m.AwayTeam] = (0, 0, 0);

                var home = teams[m.HomeTeam]; var away = teams[m.AwayTeam];
                home.GF += m.HomeGoals; home.GD += m.HomeGoals - m.AwayGoals;
                away.GF += m.AwayGoals; away.GD += m.AwayGoals - m.HomeGoals;

                if (m.HomeGoals > m.AwayGoals) home.Pts += 3;
                else if (m.HomeGoals < m.AwayGoals) away.Pts += 3;
                else { home.Pts++; away.Pts++; }

                teams[m.HomeTeam] = home; teams[m.AwayTeam] = away;
            }

            var champion = teams.OrderByDescending(t => t.Value.Pts)
                .ThenByDescending(t => t.Value.GD)
                .ThenByDescending(t => t.Value.GF)
                .First();

            sb.AppendLine($"  {season}: {champion.Key} ({champion.Value.Pts} pts, GD: {champion.Value.GD:+0;-0})");
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("List available seasons and match counts for a competition.")]
    public static string GetCompetitionSummary(
        [Description("Competition: 'Brasileirão', 'Copa do Brasil', 'Libertadores', or leave empty for all.")] string? competition = null)
    {
        var query = Data.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        var matches = query.ToList();

        if (matches.Count == 0)
            return "No match data found.";

        var sb = new StringBuilder();
        sb.AppendLine("Competition Summary:");
        sb.AppendLine();

        // By competition
        var byComp = matches.GroupBy(m => m.Competition).OrderBy(g => g.Key);
        foreach (var g in byComp)
        {
            var seasons = g.Where(m => m.Season.HasValue).Select(m => m.Season!.Value).Distinct().OrderBy(s => s).ToList();
            sb.AppendLine($"  {g.Key}: {g.Count()} matches, seasons: {string.Join(", ", seasons)}");
        }

        sb.AppendLine();
        sb.AppendLine($"  Total matches loaded: {Data.Matches.Count}");
        sb.AppendLine($"  Total players loaded: {Data.Players.Count}");
        sb.AppendLine($"  Unique teams: {Data.Matches.SelectMany(m => new[] { m.HomeTeam, m.AwayTeam }).Distinct().Count()}");

        return sb.ToString().TrimEnd();
    }
}