using BrazilianSoccerMCP.Data;
using BrazilianSoccerMCP.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMCP.Tools;

[McpServerToolType]
public class SoccerTools
{
    private readonly List<UnifiedMatch> _matches;
    private readonly List<FifaPlayer> _players;
    private readonly DataLoader _loader;

    public SoccerTools()
    {
        _loader = new DataLoader();
        _matches = _loader.LoadAllUnifiedMatches();
        _players = _loader.LoadFifaPlayers();
    }

    // ── Competition name normalization ──────────────────────────────

    private static readonly Dictionary<string, string> CompetitionAliases = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Brasileirão"] = "Brasileirão",
        ["Brasileirao"] = "Brasileirão",
        ["Serie A"] = "Brasileirão",
        ["Campeonato Brasileiro"] = "Brasileirão",
        ["Copa do Brasil"] = "Copa do Brasil",
        ["Copa Brasil"] = "Copa do Brasil",
        ["Libertadores"] = "Libertadores",
        ["Copa Libertadores"] = "Libertadores",
    };

    private static string? NormalizeCompetition(string? input)
    {
        if (string.IsNullOrWhiteSpace(input))
            return null;

        if (CompetitionAliases.TryGetValue(input.Trim(), out var canonical))
            return canonical;

        return input.Trim();
    }

    private static bool CompetitionMatches(UnifiedMatch m, string normalized)
    {
        return string.Equals(m.Competition, normalized, StringComparison.OrdinalIgnoreCase);
    }

    // ── Date parsing ────────────────────────────────────────────────

    private static readonly string[] DateFormats =
    [
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "MM/dd/yyyy",
        "yyyy/MM/dd",
        "dd-MM-yyyy",
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-ddTHH:mm:ss",
    ];

    private static DateTime? ParseDate(string? input)
    {
        if (string.IsNullOrWhiteSpace(input))
            return null;

        if (DateTime.TryParseExact(input.Trim(), DateFormats,
                System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.None, out var dt))
            return dt;

        if (DateTime.TryParse(input.Trim(),
                System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.None, out dt))
            return dt;

        return null;
    }

    // ── Formatting helpers ──────────────────────────────────────────

    private static string FormatDate(DateTime? date)
    {
        return date?.ToString("yyyy-MM-dd") ?? "??-??-??";
    }

    // ════════════════════════════════════════════════════════════════
    //  MATCH QUERIES
    // ════════════════════════════════════════════════════════════════

    [McpServerTool]
    public string search_matches(
        string? home_team = null,
        string? away_team = null,
        string? team = null,
        int? season = null,
        string? competition = null,
        string? date_from = null,
        string? date_to = null)
    {
        var canonicalCompetition = NormalizeCompetition(competition);
        var from = ParseDate(date_from);
        var to = ParseDate(date_to);

        var results = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(home_team))
        {
            var normalized = TeamNormalizer.Normalize(home_team);
            results = results.Where(m => TeamNormalizer.Matches(m.HomeTeam, home_team));
        }

        if (!string.IsNullOrWhiteSpace(away_team))
        {
            results = results.Where(m => TeamNormalizer.Matches(m.AwayTeam, away_team));
        }

        if (!string.IsNullOrWhiteSpace(team))
        {
            results = results.Where(m =>
                TeamNormalizer.Matches(m.HomeTeam, team) ||
                TeamNormalizer.Matches(m.AwayTeam, team));
        }

        if (season.HasValue)
            results = results.Where(m => m.Season == season.Value);

        if (canonicalCompetition is not null)
            results = results.Where(m => CompetitionMatches(m, canonicalCompetition));

        if (from.HasValue)
            results = results.Where(m => m.Date.HasValue && m.Date.Value >= from.Value);

        if (to.HasValue)
            results = results.Where(m => m.Date.HasValue && m.Date.Value <= to.Value);

        var list = results.OrderBy(m => m.Date).ToList();

        if (list.Count == 0)
            return "No matches found.";

        var sb = new System.Text.StringBuilder();

        var descParts = new List<string>();
        if (!string.IsNullOrWhiteSpace(home_team)) descParts.Add($"{home_team} (home)");
        if (!string.IsNullOrWhiteSpace(away_team)) descParts.Add($"{away_team} (away)");
        if (!string.IsNullOrWhiteSpace(team) && string.IsNullOrWhiteSpace(home_team) && string.IsNullOrWhiteSpace(away_team))
            descParts.Add(team);
        if (season.HasValue) descParts.Add(season.Value.ToString());
        if (canonicalCompetition is not null) descParts.Add(canonicalCompetition);

        sb.AppendLine(descParts.Count > 0
            ? $"Matches for {string.Join(", ", descParts)}:"
            : "Matches:");

        foreach (var m in list)
        {
            var roundInfo = !string.IsNullOrWhiteSpace(m.Round) ? $", Round {m.Round}"
                          : !string.IsNullOrWhiteSpace(m.Stage) ? $", {m.Stage}"
                          : "";
            sb.AppendLine($"  {FormatDate(m.Date)}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition}{roundInfo})");
        }

        sb.AppendLine();
        sb.AppendLine($"Found {list.Count} matches.");
        return sb.ToString();
    }

    [McpServerTool]
    public string head_to_head(string team1, string team2)
    {
        var matches = _matches.Where(m =>
            (TeamNormalizer.Matches(m.HomeTeam, team1) && TeamNormalizer.Matches(m.AwayTeam, team2)) ||
            (TeamNormalizer.Matches(m.HomeTeam, team2) && TeamNormalizer.Matches(m.AwayTeam, team1)))
            .OrderBy(m => m.Date)
            .ToList();

        if (matches.Count == 0)
            return $"No matches found between {team1} and {team2}.";

        int team1Wins = 0, team2Wins = 0, draws = 0;
        int team1Goals = 0, team2Goals = 0;

        foreach (var m in matches)
        {
            bool team1IsHome = TeamNormalizer.Matches(m.HomeTeam, team1);
            double goalsFor = team1IsHome ? m.HomeGoals : m.AwayGoals;
            double goalsAgainst = team1IsHome ? m.AwayGoals : m.HomeGoals;

            team1Goals += (int)goalsFor;
            team2Goals += (int)goalsAgainst;

            if (goalsFor > goalsAgainst)
                team1Wins++;
            else if (goalsFor < goalsAgainst)
                team2Wins++;
            else
                draws++;
        }

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Head-to-Head: {team1} vs {team2}");
        sb.AppendLine($"  Total matches: {matches.Count}");
        sb.AppendLine($"  {team1}: {team1Wins} wins, {team2}: {team2Wins} wins, Draws: {draws}");
        sb.AppendLine($"  Goals: {team1} {team1Goals} - {team2Goals} {team2}");
        sb.AppendLine();
        sb.AppendLine("Matches:");

        foreach (var m in matches)
        {
            sb.AppendLine($"  {FormatDate(m.Date)}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} ({m.Competition})");
        }

        return sb.ToString();
    }

    // ════════════════════════════════════════════════════════════════
    //  TEAM QUERIES
    // ════════════════════════════════════════════════════════════════

    [McpServerTool]
    public string team_statistics(string team, int? season = null, string? competition = null)
    {
        var canonicalCompetition = NormalizeCompetition(competition);

        var matches = _matches.Where(m =>
            TeamNormalizer.Matches(m.HomeTeam, team) ||
            TeamNormalizer.Matches(m.AwayTeam, team));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        if (canonicalCompetition is not null)
            matches = matches.Where(m => CompetitionMatches(m, canonicalCompetition));

        var list = matches.OrderBy(m => m.Date).ToList();

        if (list.Count == 0)
            return $"No matches found for {team}.";

        int played = 0, wins = 0, draws = 0, losses = 0;
        int goalsFor = 0, goalsAgainst = 0;

        foreach (var m in list)
        {
            played++;
            bool isHome = TeamNormalizer.Matches(m.HomeTeam, team);
            double gf = isHome ? m.HomeGoals : m.AwayGoals;
            double ga = isHome ? m.AwayGoals : m.HomeGoals;
            goalsFor += (int)gf;
            goalsAgainst += (int)ga;

            if (gf > ga) wins++;
            else if (gf < ga) losses++;
            else draws++;
        }

        double winRate = played > 0 ? (double)wins / played * 100.0 : 0;
        int points = wins * 3 + draws;

        var header = $"{team} Statistics";
        if (season.HasValue) header += $" ({season.Value}";
        if (canonicalCompetition is not null)
            header += season.HasValue ? $" {canonicalCompetition})" : $" ({canonicalCompetition})";
        else if (season.HasValue) header += ")";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine(header);
        sb.AppendLine($"  Matches: {played}");
        sb.AppendLine($"  Wins: {wins}, Draws: {draws}, Losses: {losses}");
        sb.AppendLine($"  Goals For: {goalsFor}, Goals Against: {goalsAgainst}");
        sb.AppendLine($"  Win Rate: {winRate:F1}%");
        sb.AppendLine($"  Points: {points}");
        return sb.ToString();
    }

    [McpServerTool]
    public string team_home_record(string team, int? season = null)
    {
        var matches = _matches.Where(m => TeamNormalizer.Matches(m.HomeTeam, team));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        var list = matches.OrderBy(m => m.Date).ToList();

        if (list.Count == 0)
            return $"No home matches found for {team}.";

        int played = 0, wins = 0, draws = 0, losses = 0;
        int goalsFor = 0, goalsAgainst = 0;

        foreach (var m in list)
        {
            played++;
            goalsFor += (int)m.HomeGoals;
            goalsAgainst += (int)m.AwayGoals;

            if (m.HomeGoals > m.AwayGoals) wins++;
            else if (m.HomeGoals < m.AwayGoals) losses++;
            else draws++;
        }

        double winRate = played > 0 ? (double)wins / played * 100.0 : 0;

        var header = $"{team} Home Record";
        if (season.HasValue) header += $" ({season.Value})";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine(header);
        sb.AppendLine($"  Matches: {played}");
        sb.AppendLine($"  Wins: {wins}, Draws: {draws}, Losses: {losses}");
        sb.AppendLine($"  Goals For: {goalsFor}, Goals Against: {goalsAgainst}");
        sb.AppendLine($"  Win Rate: {winRate:F1}%");
        return sb.ToString();
    }

    [McpServerTool]
    public string team_away_record(string team, int? season = null)
    {
        var matches = _matches.Where(m => TeamNormalizer.Matches(m.AwayTeam, team));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        var list = matches.OrderBy(m => m.Date).ToList();

        if (list.Count == 0)
            return $"No away matches found for {team}.";

        int played = 0, wins = 0, draws = 0, losses = 0;
        int goalsFor = 0, goalsAgainst = 0;

        foreach (var m in list)
        {
            played++;
            goalsFor += (int)m.AwayGoals;
            goalsAgainst += (int)m.HomeGoals;

            if (m.AwayGoals > m.HomeGoals) wins++;
            else if (m.AwayGoals < m.HomeGoals) losses++;
            else draws++;
        }

        double winRate = played > 0 ? (double)wins / played * 100.0 : 0;

        var header = $"{team} Away Record";
        if (season.HasValue) header += $" ({season.Value})";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine(header);
        sb.AppendLine($"  Matches: {played}");
        sb.AppendLine($"  Wins: {wins}, Draws: {draws}, Losses: {losses}");
        sb.AppendLine($"  Goals For: {goalsFor}, Goals Against: {goalsAgainst}");
        sb.AppendLine($"  Win Rate: {winRate:F1}%");
        return sb.ToString();
    }

    // ════════════════════════════════════════════════════════════════
    //  PLAYER QUERIES
    // ════════════════════════════════════════════════════════════════

    [McpServerTool]
    public string search_players(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? min_overall = null,
        int limit = 20)
    {
        var results = _players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            results = results.Where(p =>
                p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            results = results.Where(p =>
                p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            results = results.Where(p =>
                p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            results = results.Where(p =>
                p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }

        if (min_overall.HasValue)
            results = results.Where(p => p.Overall >= min_overall.Value);

        results = results.OrderByDescending(p => p.Overall);

        var list = results.Take(limit).ToList();
        var totalCount = results.Count();

        if (list.Count == 0)
            return "No players found matching the criteria.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Players found:");
        sb.AppendLine();

        int rank = 1;
        foreach (var p in list)
        {
            sb.AppendLine($"  {rank}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}, Nationality: {p.Nationality}");
            rank++;
        }

        if (totalCount > limit)
            sb.AppendLine($"  ... and {totalCount - limit} more (showing top {limit} of {totalCount})");

        return sb.ToString();
    }

    [McpServerTool]
    public string team_players(string club)
    {
        var players = _players
            .Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .ToList();

        if (players.Count == 0)
            return $"No players found for club: {club}";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Players at {club}:");
        sb.AppendLine($"  Total: {players.Count}");
        if (players.Count > 0)
        {
            double avgOverall = players.Average(p => p.Overall);
            sb.AppendLine($"  Average Overall Rating: {avgOverall:F1}");
        }
        sb.AppendLine();

        int rank = 1;
        foreach (var p in players)
        {
            sb.AppendLine($"  {rank}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Age: {p.Age}, Nationality: {p.Nationality}");
            rank++;
        }

        return sb.ToString();
    }

    // ════════════════════════════════════════════════════════════════
    //  COMPETITION QUERIES
    // ════════════════════════════════════════════════════════════════

    [McpServerTool]
    public string competition_standings(string competition, int season)
    {
        var canonicalCompetition = NormalizeCompetition(competition);
        if (canonicalCompetition is null)
            return $"Unknown competition: {competition}";

        var matches = _matches
            .Where(m => CompetitionMatches(m, canonicalCompetition) && m.Season == season)
            .ToList();

        if (matches.Count == 0)
            return $"No matches found for {canonicalCompetition} {season}.";

        var teams = new Dictionary<string, (int Pts, int W, int D, int L, int GF, int GA)>
            (StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            void AddTeam(string team, double gf, double ga)
            {
                if (!teams.ContainsKey(team))
                    teams[team] = (0, 0, 0, 0, 0, 0);

                var s = teams[team];
                int goalsF = (int)gf;
                int goalsA = (int)ga;
                int pts = 0, w = 0, d = 0, l = 0;

                if (gf > ga) { w = 1; pts = 3; }
                else if (gf < ga) { l = 1; }
                else { d = 1; pts = 1; }

                teams[team] = (s.Pts + pts, s.W + w, s.D + d, s.L + l, s.GF + goalsF, s.GA + goalsA);
            }

            AddTeam(m.HomeTeam, m.HomeGoals, m.AwayGoals);
            AddTeam(m.AwayTeam, m.AwayGoals, m.HomeGoals);
        }

        var standings = teams
            .Select(t => new
            {
                Team = t.Key,
                t.Value.Pts,
                t.Value.W,
                t.Value.D,
                t.Value.L,
                t.Value.GF,
                t.Value.GA,
                GD = t.Value.GF - t.Value.GA
            })
            .OrderByDescending(t => t.Pts)
            .ThenByDescending(t => t.GD)
            .ThenByDescending(t => t.GF)
            .ToList();

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{canonicalCompetition} {season} Standings:");
        sb.AppendLine();

        int pos = 1;
        foreach (var t in standings)
        {
            sb.AppendLine($"  {pos,2}. {t.Team} - {t.Pts} pts ({t.W}W, {t.D}D, {t.L}L) GF:{t.GF} GA:{t.GA} GD:{t.GD:+0;-0;0}");
            pos++;
        }

        return sb.ToString();
    }

    [McpServerTool]
    public string competition_winners(string competition)
    {
        var canonicalCompetition = NormalizeCompetition(competition);
        if (canonicalCompetition is null)
            return $"Unknown competition: {competition}";

        var matches = _matches
            .Where(m => CompetitionMatches(m, canonicalCompetition) && m.Season.HasValue)
            .ToList();

        if (matches.Count == 0)
            return $"No matches found for {canonicalCompetition}.";

        var seasons = matches
            .GroupBy(m => m.Season!.Value)
            .OrderBy(s => s.Key);

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{canonicalCompetition} Winners by Season:");
        sb.AppendLine();

        foreach (var seasonGroup in seasons)
        {
            var teams = new Dictionary<string, (int Pts, double GF, double GA)>
                (StringComparer.OrdinalIgnoreCase);

            foreach (var m in seasonGroup)
            {
                void AddTeam(string team, double gf, double ga)
                {
                    if (!teams.ContainsKey(team))
                        teams[team] = (0, 0, 0);
                    var s = teams[team];
                    int pts = gf > ga ? 3 : gf < ga ? 0 : 1;
                    teams[team] = (s.Pts + pts, s.GF + gf, s.GA + ga);
                }

                AddTeam(m.HomeTeam, m.HomeGoals, m.AwayGoals);
                AddTeam(m.AwayTeam, m.AwayGoals, m.HomeGoals);
            }

            var winner = teams
                .OrderByDescending(t => t.Value.Pts)
                .ThenByDescending(t => t.Value.GF - t.Value.GA)
                .ThenByDescending(t => t.Value.GF)
                .First();

            sb.AppendLine($"  {seasonGroup.Key}: {winner.Key} ({winner.Value.Pts} pts)");
        }

        return sb.ToString();
    }

    // ════════════════════════════════════════════════════════════════
    //  STATISTICAL ANALYSIS
    // ════════════════════════════════════════════════════════════════

    [McpServerTool]
    public string biggest_wins(int limit = 10, string? competition = null)
    {
        var canonicalCompetition = NormalizeCompetition(competition);

        var query = _matches.AsEnumerable();

        if (canonicalCompetition is not null)
            query = query.Where(m => CompetitionMatches(m, canonicalCompetition));

        var results = query
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .ThenBy(m => m.Date)
            .Take(limit)
            .ToList();

        if (results.Count == 0)
            return "No matches found.";

        var header = canonicalCompetition is not null
            ? $"Biggest Wins in {canonicalCompetition}:"
            : "Biggest Wins:";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine(header);
        sb.AppendLine();

        int rank = 1;
        foreach (var m in results)
        {
            double diff = Math.Abs(m.HomeGoals - m.AwayGoals);
            string winner = m.HomeGoals > m.AwayGoals ? m.HomeTeam : m.AwayTeam;
            sb.AppendLine($"  {rank}. {FormatDate(m.Date)}: {m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam} (Goal difference: {diff:F0})");
            rank++;
        }

        return sb.ToString();
    }

    [McpServerTool]
    public string goals_per_match_average(string? competition = null, int? season = null)
    {
        var canonicalCompetition = NormalizeCompetition(competition);

        var matches = _matches.AsEnumerable();

        if (canonicalCompetition is not null)
            matches = matches.Where(m => CompetitionMatches(m, canonicalCompetition));

        if (season.HasValue)
            matches = matches.Where(m => m.Season == season.Value);

        var list = matches.ToList();

        if (list.Count == 0)
            return "No matches found for the specified criteria.";

        double totalGoals = list.Sum(m => m.HomeGoals + m.AwayGoals);
        double avgGoals = totalGoals / list.Count;

        int homeWins = list.Count(m => m.HomeGoals > m.AwayGoals);
        int awayWins = list.Count(m => m.AwayGoals > m.HomeGoals);
        int draws = list.Count(m => m.HomeGoals == m.AwayGoals);

        var sb = new System.Text.StringBuilder();

        var descParts = new List<string>();
        if (canonicalCompetition is not null) descParts.Add(canonicalCompetition);
        if (season.HasValue) descParts.Add(season.Value.ToString());
        var desc = descParts.Count > 0 ? string.Join(" ", descParts) : "All Competitions";

        sb.AppendLine($"Goals Per Match Average ({desc}):");
        sb.AppendLine($"  Matches analyzed: {list.Count}");
        sb.AppendLine($"  Total goals: {totalGoals:F0}");
        sb.AppendLine($"  Average goals per match: {avgGoals:F2}");
        sb.AppendLine($"  Home wins: {homeWins} ({(double)homeWins / list.Count * 100:F1}%)");
        sb.AppendLine($"  Away wins: {awayWins} ({(double)awayWins / list.Count * 100:F1}%)");
        sb.AppendLine($"  Draws: {draws} ({(double)draws / list.Count * 100:F1}%)");
        return sb.ToString();
    }

    [McpServerTool]
    public string team_season_comparison(string team, int season1, int season2)
    {
        static (int P, int W, int D, int L, int GF, int GA) CalcStats(IEnumerable<UnifiedMatch> matches, string t)
        {
            int p = 0, w = 0, d = 0, l = 0, gf = 0, ga = 0;
            foreach (var m in matches)
            {
                p++;
                bool isHome = TeamNormalizer.Matches(m.HomeTeam, t);
                double goalsFor = isHome ? m.HomeGoals : m.AwayGoals;
                double goalsAgainst = isHome ? m.AwayGoals : m.HomeGoals;
                gf += (int)goalsFor;
                ga += (int)goalsAgainst;

                if (goalsFor > goalsAgainst) w++;
                else if (goalsFor < goalsAgainst) l++;
                else d++;
            }
            return (p, w, d, l, gf, ga);
        }

        var s1 = CalcStats(
            _matches.Where(m => m.Season == season1 &&
                (TeamNormalizer.Matches(m.HomeTeam, team) || TeamNormalizer.Matches(m.AwayTeam, team))),
            team);

        var s2 = CalcStats(
            _matches.Where(m => m.Season == season2 &&
                (TeamNormalizer.Matches(m.HomeTeam, team) || TeamNormalizer.Matches(m.AwayTeam, team))),
            team);

        if (s1.P == 0 && s2.P == 0)
            return $"No matches found for {team} in seasons {season1} and {season2}.";

        double wr1 = s1.P > 0 ? (double)s1.W / s1.P * 100 : 0;
        double wr2 = s2.P > 0 ? (double)s2.W / s2.P * 100 : 0;
        int pts1 = s1.W * 3 + s1.D;
        int pts2 = s2.W * 3 + s2.D;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{team}: {season1} vs {season2} Comparison");
        sb.AppendLine();
        sb.AppendLine($"  {"Statistic",-20} {season1,-10} {season2,-10}");
        sb.AppendLine($"  {"--------------------",-20} {"----------",-10} {"----------",-10}");
        sb.AppendLine($"  {"Matches",-20} {s1.P,-10} {s2.P,-10}");
        sb.AppendLine($"  {"Wins",-20} {s1.W,-10} {s2.W,-10}");
        sb.AppendLine($"  {"Draws",-20} {s1.D,-10} {s2.D,-10}");
        sb.AppendLine($"  {"Losses",-20} {s1.L,-10} {s2.L,-10}");
        sb.AppendLine($"  {"Goals For",-20} {s1.GF,-10} {s2.GF,-10}");
        sb.AppendLine($"  {"Goals Against",-20} {s1.GA,-10} {s2.GA,-10}");
        sb.AppendLine($"  {"Win Rate",-20} {wr1,2:F1}%{"",-4} {wr2,2:F1}%");
        sb.AppendLine($"  {"Points",-20} {pts1,-10} {pts2,-10}");
        return sb.ToString();
    }
}