using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Text;

namespace BrazilianSoccerMcp;

[McpServerToolType]
public class SoccerTools(SoccerDatabase db)
{
    private const int MaxMatchesInResponse = 50;

    [McpServerTool(Name = "search_matches")]
    [Description("Search for soccer matches by team, season, competition, or date range. Returns match results with scores.")]
    public string SearchMatches(
        [Description("Team name to search for (searches both home and away). E.g. 'Flamengo', 'Palmeiras'")] string? team = null,
        [Description("Season/year to filter by, e.g. 2023")] int? season = null,
        [Description("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores'")] string? competition = null,
        [Description("Start date filter in yyyy-MM-dd format")] string? fromDate = null,
        [Description("End date filter in yyyy-MM-dd format")] string? toDate = null,
        [Description("Home team name filter")] string? homeTeam = null,
        [Description("Away team name filter")] string? awayTeam = null,
        [Description("Maximum number of results to return (default 20, max 50)")] int limit = 20)
    {
        DateTime? from = fromDate != null ? DateTime.TryParse(fromDate, out var d1) ? d1 : null : null;
        DateTime? to = toDate != null ? DateTime.TryParse(toDate, out var d2) ? d2 : null : null;

        var matches = db.SearchMatches(team, homeTeam, awayTeam, season, competition, from, to)
            .OrderByDescending(m => m.Date)
            .ToList();

        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        int shown = Math.Min(limit, MaxMatchesInResponse);
        var sb = new StringBuilder();
        sb.AppendLine($"Found {matches.Count} match(es). Showing top {Math.Min(shown, matches.Count)}:\n");

        foreach (var m in matches.Take(shown))
        {
            var date = m.Date != DateTime.MinValue ? m.Date.ToString("yyyy-MM-dd") : "Unknown date";
            var round = !string.IsNullOrEmpty(m.Round) ? $" Round {m.Round}" : "";
            var stage = !string.IsNullOrEmpty(m.Stage) ? $" ({m.Stage})" : "";
            sb.AppendLine($"- {date}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} [{m.Competition}{round}{stage}] Season: {m.Season}");
        }

        if (matches.Count > shown)
            sb.AppendLine($"\n... and {matches.Count - shown} more matches.");

        return sb.ToString();
    }

    [McpServerTool(Name = "get_head_to_head")]
    [Description("Get head-to-head record between two teams across all competitions and seasons.")]
    public string GetHeadToHead(
        [Description("First team name, e.g. 'Flamengo'")] string team1,
        [Description("Second team name, e.g. 'Fluminense'")] string team2,
        [Description("Optional season/year filter")] int? season = null,
        [Description("Optional competition filter")] string? competition = null)
    {
        var matches = db.AllMatches.Where(m =>
        {
            bool t1Home = DataLoader.TeamMatches(m.HomeTeam, team1) && DataLoader.TeamMatches(m.AwayTeam, team2);
            bool t2Home = DataLoader.TeamMatches(m.HomeTeam, team2) && DataLoader.TeamMatches(m.AwayTeam, team1);
            if (!t1Home && !t2Home) return false;
            if (season.HasValue && m.Season != season.Value) return false;
            if (competition != null && !m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) return false;
            return true;
        })
        .OrderByDescending(m => m.Date)
        .ToList();

        if (matches.Count == 0)
            return $"No matches found between '{team1}' and '{team2}'.";

        int t1Wins = 0, t2Wins = 0, draws = 0;
        int t1Goals = 0, t2Goals = 0;

        foreach (var m in matches)
        {
            bool t1Home = DataLoader.TeamMatches(m.HomeTeam, team1);
            int t1G = t1Home ? m.HomeGoals : m.AwayGoals;
            int t2G = t1Home ? m.AwayGoals : m.HomeGoals;
            t1Goals += t1G; t2Goals += t2G;
            if (t1G > t2G) t1Wins++;
            else if (t1G < t2G) t2Wins++;
            else draws++;
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Head-to-head: {team1} vs {team2}");
        sb.AppendLine($"Total matches: {matches.Count}");
        sb.AppendLine($"{team1}: {t1Wins} wins, Goals: {t1Goals}");
        sb.AppendLine($"{team2}: {t2Wins} wins, Goals: {t2Goals}");
        sb.AppendLine($"Draws: {draws}");
        sb.AppendLine();
        sb.AppendLine("Recent matches:");

        foreach (var m in matches.Take(20))
        {
            var date = m.Date != DateTime.MinValue ? m.Date.ToString("yyyy-MM-dd") : "Unknown";
            sb.AppendLine($"- {date}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} [{m.Competition}, {m.Season}]");
        }

        if (matches.Count > 20)
            sb.AppendLine($"... and {matches.Count - 20} more.");

        return sb.ToString();
    }

    [McpServerTool(Name = "get_team_stats")]
    [Description("Get statistics for a team including wins, losses, draws, goals scored and conceded.")]
    public string GetTeamStats(
        [Description("Team name, e.g. 'Palmeiras', 'Flamengo'")] string team,
        [Description("Season/year filter, e.g. 2023")] int? season = null,
        [Description("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores'")] string? competition = null,
        [Description("If true, only home matches; if false, only away matches; if not set, all matches")] bool? homeOnly = null)
    {
        var stats = db.CalculateTeamStats(team, season, competition, homeOnly);

        if (stats.Matches == 0)
            return $"No matches found for '{team}'" +
                   (season.HasValue ? $" in {season}" : "") +
                   (competition != null ? $" ({competition})" : "") + ".";

        var context = homeOnly == true ? " (Home only)" : homeOnly == false ? " (Away only)" : "";
        var sb = new StringBuilder();
        sb.AppendLine($"Statistics for {team}{context}:");
        if (season.HasValue) sb.AppendLine($"Season: {season}");
        if (competition != null) sb.AppendLine($"Competition: {competition}");
        sb.AppendLine($"Matches: {stats.Matches}");
        sb.AppendLine($"Wins: {stats.Wins} | Draws: {stats.Draws} | Losses: {stats.Losses}");
        sb.AppendLine($"Points: {stats.Points}");
        sb.AppendLine($"Goals For: {stats.GoalsFor} | Goals Against: {stats.GoalsAgainst} | Diff: {stats.GoalDiff:+#;-#;0}");
        sb.AppendLine($"Win Rate: {stats.WinRate:F1}%");
        sb.AppendLine($"Avg Goals Scored: {(stats.Matches > 0 ? (double)stats.GoalsFor / stats.Matches : 0):F2}");
        sb.AppendLine($"Avg Goals Conceded: {(stats.Matches > 0 ? (double)stats.GoalsAgainst / stats.Matches : 0):F2}");

        return sb.ToString();
    }

    [McpServerTool(Name = "get_standings")]
    [Description("Get league standings for a specific season, calculated from match results.")]
    public string GetStandings(
        [Description("Season year, e.g. 2023")] int season,
        [Description("Competition name (default: Brasileirão)")] string competition = "Brasileirão")
    {
        var standings = db.GetStandings(season, competition);

        if (standings.Count == 0)
            return $"No standings data found for {season} {competition}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{season} {competition} Standings (calculated from match data):");
        sb.AppendLine($"{"Pos",-4} {"Team",-30} {"P",-4} {"W",-4} {"D",-4} {"L",-4} {"GF",-4} {"GA",-4} {"GD",-6} {"Pts",-4}");
        sb.AppendLine(new string('-', 70));

        int pos = 1;
        foreach (var s in standings)
        {
            var gd = s.GoalDiff >= 0 ? $"+{s.GoalDiff}" : s.GoalDiff.ToString();
            sb.AppendLine($"{pos,-4} {s.Team,-30} {s.Matches,-4} {s.Wins,-4} {s.Draws,-4} {s.Losses,-4} {s.GoalsFor,-4} {s.GoalsAgainst,-4} {gd,-6} {s.Points,-4}");
            pos++;
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "search_players")]
    [Description("Search for players in the FIFA dataset by name, nationality, club, or position.")]
    public string SearchPlayers(
        [Description("Player name to search (partial match supported)")] string? name = null,
        [Description("Player nationality, e.g. 'Brazil', 'Argentina'")] string? nationality = null,
        [Description("Club name, e.g. 'Flamengo', 'Palmeiras', 'FC Barcelona'")] string? club = null,
        [Description("Position, e.g. 'GK', 'ST', 'CAM', 'CB'")] string? position = null,
        [Description("Minimum overall rating (1-99)")] int? minRating = null,
        [Description("Maximum number of results to return (default 20)")] int limit = 20)
    {
        var players = db.SearchPlayers(name, nationality, club, position, minRating, limit: Math.Min(limit, 100)).ToList();

        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s):\n");

        foreach (var p in players)
        {
            sb.AppendLine($"- {p.Name} | Age: {p.Age} | Nationality: {p.Nationality}");
            sb.AppendLine($"  Overall: {p.Overall} | Potential: {p.Potential} | Position: {p.Position}");
            sb.AppendLine($"  Club: {p.Club} | Jersey: #{p.JerseyNumber} | Height: {p.Height} | Weight: {p.Weight}");
            if (p.Value != null) sb.AppendLine($"  Value: {p.Value} | Wage: {p.Wage}");
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_biggest_wins")]
    [Description("Find the biggest victories (largest goal differences) in the dataset.")]
    public string GetBiggestWins(
        [Description("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores'")] string? competition = null,
        [Description("Season/year filter")] int? season = null,
        [Description("Team name to filter (optional)")] string? team = null,
        [Description("Number of results to return (default 10)")] int limit = 10)
    {
        var matches = db.AllMatches.AsEnumerable();
        if (competition != null) matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue) matches = matches.Where(m => m.Season == season.Value);
        if (team != null) matches = matches.Where(m => DataLoader.TeamMatches(m.HomeTeam, team) || DataLoader.TeamMatches(m.AwayTeam, team));

        var biggest = matches
            .Where(m => m.HomeGoals != m.AwayGoals)
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .ThenByDescending(m => m.HomeGoals + m.AwayGoals)
            .Take(Math.Min(limit, 50))
            .ToList();

        if (biggest.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Biggest wins{(competition != null ? $" in {competition}" : "")}:\n");

        int i = 1;
        foreach (var m in biggest)
        {
            var date = m.Date != DateTime.MinValue ? m.Date.ToString("yyyy-MM-dd") : "Unknown";
            var diff = Math.Abs(m.HomeGoals - m.AwayGoals);
            sb.AppendLine($"{i}. {date}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} (margin: {diff}) [{m.Competition}, {m.Season}]");
            i++;
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_competition_summary")]
    [Description("Get a summary of a competition for a given season including match count, goals, and top teams.")]
    public string GetCompetitionSummary(
        [Description("Competition name: 'Brasileirão', 'Copa do Brasil', 'Libertadores', or leave empty for all")] string? competition = null,
        [Description("Season/year to summarize")] int? season = null)
    {
        var matches = db.AllMatches.AsEnumerable();
        if (competition != null) matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        if (season.HasValue) matches = matches.Where(m => m.Season == season.Value);
        var list = matches.ToList();

        if (list.Count == 0)
            return "No data found for the given criteria.";

        int totalGoals = list.Sum(m => m.HomeGoals + m.AwayGoals);
        int homeWins = list.Count(m => m.HomeGoals > m.AwayGoals);
        int awayWins = list.Count(m => m.AwayGoals > m.HomeGoals);
        int draws = list.Count(m => m.HomeGoals == m.AwayGoals);

        var teamGoals = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var m in list)
        {
            teamGoals[m.HomeTeam] = teamGoals.GetValueOrDefault(m.HomeTeam) + m.HomeGoals;
            teamGoals[m.AwayTeam] = teamGoals.GetValueOrDefault(m.AwayTeam) + m.AwayGoals;
        }
        var topScoring = teamGoals.OrderByDescending(kv => kv.Value).Take(5).ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Competition Summary: {competition ?? "All"}{(season.HasValue ? $" {season}" : "")}");
        sb.AppendLine($"Total Matches: {list.Count}");
        sb.AppendLine($"Total Goals: {totalGoals} (avg {(double)totalGoals / list.Count:F2} per match)");
        sb.AppendLine($"Home Wins: {homeWins} ({(double)homeWins / list.Count * 100:F1}%)");
        sb.AppendLine($"Away Wins: {awayWins} ({(double)awayWins / list.Count * 100:F1}%)");
        sb.AppendLine($"Draws: {draws} ({(double)draws / list.Count * 100:F1}%)");

        if (season.HasValue)
        {
            var seasons = list.Select(m => m.Season).Distinct().OrderBy(s => s).ToList();
            sb.AppendLine($"Seasons covered: {string.Join(", ", seasons)}");
        }

        sb.AppendLine("\nTop Goal-Scoring Teams:");
        int rank = 1;
        foreach (var kv in topScoring)
        {
            sb.AppendLine($"{rank}. {kv.Key}: {kv.Value} goals");
            rank++;
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_team_competitions")]
    [Description("Find all competitions a team has participated in.")]
    public string GetTeamCompetitions(
        [Description("Team name, e.g. 'Palmeiras'")] string team)
    {
        var matches = db.AllMatches
            .Where(m => DataLoader.TeamMatches(m.HomeTeam, team) || DataLoader.TeamMatches(m.AwayTeam, team))
            .ToList();

        if (matches.Count == 0)
            return $"No matches found for '{team}'.";

        var competitions = matches
            .GroupBy(m => m.Competition)
            .Select(g => new
            {
                Competition = g.Key,
                Matches = g.Count(),
                Seasons = g.Select(m => m.Season).Where(s => s > 0).Distinct().OrderBy(s => s).ToList(),
            })
            .OrderByDescending(c => c.Matches)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Competitions for {team}:");
        sb.AppendLine($"Total matches across all competitions: {matches.Count}\n");

        foreach (var c in competitions)
        {
            var seasonRange = c.Seasons.Count > 0
                ? $" (Seasons: {c.Seasons.First()}-{c.Seasons.Last()})"
                : "";
            sb.AppendLine($"- {c.Competition}: {c.Matches} matches{seasonRange}");
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_season_list")]
    [Description("List all available seasons and competitions in the database.")]
    public string GetSeasonList()
    {
        var byComp = db.AllMatches
            .Where(m => m.Season > 0)
            .GroupBy(m => m.Competition)
            .Select(g => new
            {
                Competition = g.Key,
                Seasons = g.Select(m => m.Season).Distinct().OrderBy(s => s).ToList(),
                Count = g.Count(),
            })
            .OrderBy(c => c.Competition)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Database contains {db.AllMatches.Count} total matches and {db.Players.Count} players.\n");
        sb.AppendLine("Competitions and seasons available:");

        foreach (var c in byComp)
        {
            var seasonRange = c.Seasons.Count > 0
                ? $"{c.Seasons.First()}-{c.Seasons.Last()}"
                : "Unknown";
            sb.AppendLine($"- {c.Competition}: {c.Count} matches ({seasonRange})");
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_top_teams")]
    [Description("Get top teams by win rate or points in a competition and season.")]
    public string GetTopTeams(
        [Description("Season/year, e.g. 2023")] int? season = null,
        [Description("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores'")] string? competition = null,
        [Description("Number of teams to return (default 10)")] int limit = 10)
    {
        var matches = db.AllMatches.AsEnumerable();
        if (season.HasValue) matches = matches.Where(m => m.Season == season.Value);
        if (competition != null) matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        var list = matches.ToList();

        if (list.Count == 0)
            return "No data found.";

        var teams = list
            .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
            .Distinct()
            .ToList();

        var stats = teams.Select(team =>
        {
            int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
            foreach (var m in list)
            {
                bool isHome = m.HomeTeam == team;
                bool isAway = m.AwayTeam == team;
                if (!isHome && !isAway) continue;
                int tg = isHome ? m.HomeGoals : m.AwayGoals;
                int og = isHome ? m.AwayGoals : m.HomeGoals;
                gf += tg; ga += og;
                if (tg > og) wins++;
                else if (tg == og) draws++;
                else losses++;
            }
            return new TeamStats { Team = team, Matches = wins + draws + losses, Wins = wins, Draws = draws, Losses = losses, GoalsFor = gf, GoalsAgainst = ga };
        })
        .Where(s => s.Matches >= 3)
        .OrderByDescending(s => s.Points)
        .ThenByDescending(s => s.GoalDiff)
        .Take(Math.Min(limit, 50))
        .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Top teams{(competition != null ? $" in {competition}" : "")}{(season.HasValue ? $" {season}" : "")}:\n");
        int pos = 1;
        foreach (var s in stats)
        {
            sb.AppendLine($"{pos}. {s.Team}: {s.Points} pts ({s.Wins}W/{s.Draws}D/{s.Losses}L) GD: {s.GoalDiff:+#;-#;0}");
            pos++;
        }

        return sb.ToString();
    }
}
