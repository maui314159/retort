using System.Globalization;
using BrazilianSoccerMcpServer.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcpServer.Services;

public sealed record TeamStats(
    string Team,
    int Matches,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    double WinRate)
{
    public override string ToString() =>
        $"{Team}: Matches {Matches}, Wins {Wins}, Draws {Draws}, Losses {Losses}, " +
        $"GF {GoalsFor}, GA {GoalsAgainst}, Win rate {WinRate:F1}%";
}

public sealed record Standing(
    string Team,
    int Points,
    int Matches,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    int GoalDifference)
{
    public override string ToString() =>
        $"{Team} - {Points} pts ({Wins}W, {Draws}D, {Losses}L) GF:{GoalsFor} GA:{GoalsAgainst} GD:{GoalDifference}";
}

public sealed record HeadToHead(
    string TeamA,
    string TeamB,
    int Matches,
    int WinsA,
    int Draws,
    int WinsB)
{
    public override string ToString() =>
        $"Head-to-head: {TeamA} {WinsA} wins, {TeamB} {WinsB} wins, {Draws} draws ({Matches} matches)";
}

public sealed class SoccerDataService
{
    private readonly List<UnifiedMatch> _matches = [];
    private readonly List<Player> _players = [];

    public SoccerDataService()
    {
        LoadData();
    }

    public IReadOnlyList<UnifiedMatch> Matches => _matches;
    public IReadOnlyList<Player> Players => _players;

    private static string DataPath(string fileName) =>
        Path.Combine(AppContext.BaseDirectory, "data", "kaggle", fileName);

    private void LoadData()
    {
        LoadBrasileirao(DataPath("Brasileirao_Matches.csv"));
        LoadCopaDoBrasil(DataPath("Brazilian_Cup_Matches.csv"));
        LoadLibertadores(DataPath("Libertadores_Matches.csv"));
        LoadBrFootball(DataPath("BR-Football-Dataset.csv"));
        LoadNovoCampeonato(DataPath("novo_campeonato_brasileiro.csv"));
        LoadFifaPlayers(DataPath("fifa_data.csv"));
    }

    private static CsvConfiguration CreateConfig() => new(CultureInfo.InvariantCulture)
    {
        HasHeaderRecord = true,
        MissingFieldFound = null,
        BadDataFound = null,
        Encoding = System.Text.Encoding.UTF8,
        PrepareHeaderForMatch = args => args.Header.Trim(),
    };

    private void LoadBrasileirao(string path)
    {
        if (!File.Exists(path)) return;
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        while (csv.Read())
        {
            var home = csv.GetField<string>("home_team") ?? string.Empty;
            var away = csv.GetField<string>("away_team") ?? string.Empty;
            _matches.Add(new UnifiedMatch
            {
                Date = csv.GetField<DateTime?>("datetime"),
                Competition = "Brasileirão",
                HomeTeam = home,
                AwayTeam = away,
                HomeTeamBase = TeamNameMatcher.BaseName(home),
                AwayTeamBase = TeamNameMatcher.BaseName(away),
                HomeState = csv.GetField<string>("home_team_state"),
                AwayState = csv.GetField<string>("away_team_state"),
                HomeGoals = csv.GetField<int?>("home_goal"),
                AwayGoals = csv.GetField<int?>("away_goal"),
                Season = csv.GetField<int?>("season"),
                Round = csv.GetField<string>("round"),
            });
        }
    }

    private void LoadCopaDoBrasil(string path)
    {
        if (!File.Exists(path)) return;
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        while (csv.Read())
        {
            var home = csv.GetField<string>("home_team") ?? string.Empty;
            var away = csv.GetField<string>("away_team") ?? string.Empty;
            _matches.Add(new UnifiedMatch
            {
                Date = csv.GetField<DateTime?>("datetime"),
                Competition = "Copa do Brasil",
                HomeTeam = home,
                AwayTeam = away,
                HomeTeamBase = TeamNameMatcher.BaseName(home),
                AwayTeamBase = TeamNameMatcher.BaseName(away),
                HomeGoals = csv.GetField<int?>("home_goal"),
                AwayGoals = csv.GetField<int?>("away_goal"),
                Season = csv.GetField<int?>("season"),
                Round = csv.GetField<string>("round"),
            });
        }
    }

    private void LoadLibertadores(string path)
    {
        if (!File.Exists(path)) return;
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        while (csv.Read())
        {
            var home = csv.GetField<string>("home_team") ?? string.Empty;
            var away = csv.GetField<string>("away_team") ?? string.Empty;
            _matches.Add(new UnifiedMatch
            {
                Date = csv.GetField<DateTime?>("datetime"),
                Competition = "Copa Libertadores",
                HomeTeam = home,
                AwayTeam = away,
                HomeTeamBase = TeamNameMatcher.BaseName(home),
                AwayTeamBase = TeamNameMatcher.BaseName(away),
                HomeGoals = csv.GetField<int?>("home_goal"),
                AwayGoals = csv.GetField<int?>("away_goal"),
                Season = csv.GetField<int?>("season"),
                Stage = csv.GetField<string>("stage"),
            });
        }
    }

    private void LoadBrFootball(string path)
    {
        if (!File.Exists(path)) return;
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        while (csv.Read())
        {
            var home = csv.GetField<string>("home") ?? string.Empty;
            var away = csv.GetField<string>("away") ?? string.Empty;
            var date = csv.GetField<DateTime?>("date");
            var competition = csv.GetField<string>("tournament") ?? "Unknown";
            _matches.Add(new UnifiedMatch
            {
                Date = date,
                Competition = competition,
                HomeTeam = home,
                AwayTeam = away,
                HomeTeamBase = TeamNameMatcher.BaseName(home),
                AwayTeamBase = TeamNameMatcher.BaseName(away),
                HomeGoals = ParseNullableInt(csv.GetField<double?>("home_goal")),
                AwayGoals = ParseNullableInt(csv.GetField<double?>("away_goal")),
                Season = date?.Year,
            });
        }
    }

    private void LoadNovoCampeonato(string path)
    {
        if (!File.Exists(path)) return;
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        while (csv.Read())
        {
            var home = csv.GetField<string>("Equipe_mandante") ?? string.Empty;
            var away = csv.GetField<string>("Equipe_visitante") ?? string.Empty;
            var dateRaw = csv.GetField<string>("Data");
            var date = DateTime.TryParseExact(
                dateRaw,
                "dd/MM/yyyy",
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out var parsed)
                ? parsed
                : (DateTime?)null;

            _matches.Add(new UnifiedMatch
            {
                Date = date,
                Competition = "Brasileirão",
                HomeTeam = home,
                AwayTeam = away,
                HomeTeamBase = TeamNameMatcher.BaseName(home),
                AwayTeamBase = TeamNameMatcher.BaseName(away),
                HomeState = csv.GetField<string>("Mandante_UF"),
                AwayState = csv.GetField<string>("Visitante_UF"),
                HomeGoals = csv.GetField<int?>("Gols_mandante"),
                AwayGoals = csv.GetField<int?>("Gols_visitante"),
                Season = csv.GetField<int?>("Ano"),
                Round = csv.GetField<string>("Rodada"),
            });
        }
    }

    private void LoadFifaPlayers(string path)
    {
        if (!File.Exists(path)) return;
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        // The first column of fifa_data.csv is unnamed; use index-based mapping.
        while (csv.Read())
        {
            _players.Add(new Player
            {
                Id = ParseIntSafe(csv.GetField<string>(1)) ?? 0,
                Name = csv.GetField<string>(2) ?? string.Empty,
                Age = ParseIntSafe(csv.GetField<string>(3)),
                Nationality = csv.GetField<string>(5) ?? string.Empty,
                Overall = ParseIntSafe(csv.GetField<string>(7)),
                Potential = ParseIntSafe(csv.GetField<string>(8)),
                Club = csv.GetField<string>(9),
                Position = csv.GetField<string>(21),
                JerseyNumber = ParseIntSafe(csv.GetField<string>(22)),
                Height = csv.GetField<string>(26),
                Weight = csv.GetField<string>(27),
            });
        }
    }

    private static int? ParseNullableInt(double? value) => value.HasValue ? (int)value.Value : null;

    private static int? ParseIntSafe(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (int.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out var result)) return result;
        return null;
    }

    public IEnumerable<UnifiedMatch> FindMatches(
        string? team = null,
        string? opponent = null,
        string? competition = null,
        int? season = null,
        DateTime? fromDate = null,
        DateTime? toDate = null,
        int limit = 50)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m =>
                TeamNameMatcher.IsMatch(m.Competition, competition) ||
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        if (fromDate.HasValue)
        {
            query = query.Where(m => m.Date >= fromDate.Value);
        }

        if (toDate.HasValue)
        {
            query = query.Where(m => m.Date <= toDate.Value);
        }

        if (!string.IsNullOrWhiteSpace(team))
        {
            query = query.Where(m =>
                TeamNameMatcher.IsMatch(m.HomeTeamBase, team) ||
                TeamNameMatcher.IsMatch(m.AwayTeamBase, team) ||
                TeamNameMatcher.IsMatch(m.HomeTeam, team) ||
                TeamNameMatcher.IsMatch(m.AwayTeam, team));
        }

        if (!string.IsNullOrWhiteSpace(opponent))
        {
            query = query.Where(m =>
                (!string.IsNullOrWhiteSpace(team) &&
                 ((TeamNameMatcher.IsMatch(m.HomeTeamBase, team) || TeamNameMatcher.IsMatch(m.HomeTeam, team)) &&
                  (TeamNameMatcher.IsMatch(m.AwayTeamBase, opponent) || TeamNameMatcher.IsMatch(m.AwayTeam, opponent)) ||
                  (TeamNameMatcher.IsMatch(m.AwayTeamBase, team) || TeamNameMatcher.IsMatch(m.AwayTeam, team)) &&
                  (TeamNameMatcher.IsMatch(m.HomeTeamBase, opponent) || TeamNameMatcher.IsMatch(m.HomeTeam, opponent)))) ||
                (string.IsNullOrWhiteSpace(team) &&
                 (TeamNameMatcher.IsMatch(m.HomeTeamBase, opponent) || TeamNameMatcher.IsMatch(m.HomeTeam, opponent) ||
                  TeamNameMatcher.IsMatch(m.AwayTeamBase, opponent) || TeamNameMatcher.IsMatch(m.AwayTeam, opponent))));
        }

        return query
            .Where(m => m.Date.HasValue)
            .OrderByDescending(m => m.Date)
            .Take(limit);
    }

    public IReadOnlyList<string> FindTeamNames(string query)
    {
        var matches = _matches
            .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Where(name => TeamNameMatcher.IsMatch(name, query))
            .Take(20)
            .ToList();

        return matches;
    }

    public TeamStats GetTeamStats(string team, int? season = null, string? competition = null, string? venue = null)
    {
        var relevant = MatchesForTeam(team, season, competition, venue)
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        var displayName = TeamNameMatcher.DisplayName(team);
        if (!relevant.Any())
        {
            return new TeamStats(displayName, 0, 0, 0, 0, 0, 0, 0.0);
        }

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var match in relevant)
        {
            var isHome = IsTeamHome(match, team);
            var teamGoals = isHome ? match.HomeGoals!.Value : match.AwayGoals!.Value;
            var oppGoals = isHome ? match.AwayGoals!.Value : match.HomeGoals!.Value;
            gf += teamGoals;
            ga += oppGoals;
            if (teamGoals > oppGoals) wins++;
            else if (teamGoals == oppGoals) draws++;
            else losses++;
        }

        var winRate = relevant.Count > 0 ? (wins * 100.0) / relevant.Count : 0.0;
        return new TeamStats(displayName, relevant.Count, wins, draws, losses, gf, ga, winRate);
    }

    public HeadToHead GetHeadToHead(string teamA, string teamB)
    {
        var relevant = _matches
            .Where(m =>
                (TeamNameMatcher.IsMatch(m.HomeTeamBase, teamA) || TeamNameMatcher.IsMatch(m.HomeTeam, teamA) ||
                 TeamNameMatcher.IsMatch(m.AwayTeamBase, teamA) || TeamNameMatcher.IsMatch(m.AwayTeam, teamA)) &&
                (TeamNameMatcher.IsMatch(m.HomeTeamBase, teamB) || TeamNameMatcher.IsMatch(m.HomeTeam, teamB) ||
                 TeamNameMatcher.IsMatch(m.AwayTeamBase, teamB) || TeamNameMatcher.IsMatch(m.AwayTeam, teamB)))
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        int winsA = 0, draws = 0, winsB = 0;
        foreach (var match in relevant)
        {
            var aIsHome = TeamNameMatcher.IsMatch(match.HomeTeamBase, teamA) || TeamNameMatcher.IsMatch(match.HomeTeam, teamA);
            var aGoals = aIsHome ? match.HomeGoals!.Value : match.AwayGoals!.Value;
            var bGoals = aIsHome ? match.AwayGoals!.Value : match.HomeGoals!.Value;
            if (aGoals > bGoals) winsA++;
            else if (aGoals == bGoals) draws++;
            else winsB++;
        }

        return new HeadToHead(
            TeamNameMatcher.DisplayName(teamA),
            TeamNameMatcher.DisplayName(teamB),
            relevant.Count,
            winsA,
            draws,
            winsB);
    }

    public IEnumerable<Standing> GetStandings(string competition, int? season = null)
    {
        var matches = _matches
            .Where(m =>
                (TeamNameMatcher.IsMatch(m.Competition, competition) || m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) &&
                (!season.HasValue || m.Season == season.Value) &&
                m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .ToList();

        var teams = matches
            .SelectMany(m => new[] { m.HomeTeamBase, m.AwayTeamBase })
            .Distinct(StringComparer.OrdinalIgnoreCase);

        var standings = new List<Standing>();
        foreach (var teamBase in teams)
        {
            var teamMatches = matches.Where(m =>
                m.HomeTeamBase.Equals(teamBase, StringComparison.OrdinalIgnoreCase) ||
                m.AwayTeamBase.Equals(teamBase, StringComparison.OrdinalIgnoreCase));

            int p = 0, w = 0, d = 0, l = 0, gf = 0, ga = 0;
            foreach (var m in teamMatches)
            {
                var isHome = m.HomeTeamBase.Equals(teamBase, StringComparison.OrdinalIgnoreCase);
                var tg = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
                var og = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;
                gf += tg;
                ga += og;
                if (tg > og) { w++; p += 3; }
                else if (tg == og) { d++; p += 1; }
                else { l++; }
            }

            standings.Add(new Standing(
                TeamNameMatcher.DisplayName(teamBase),
                p, w + d + l, w, d, l, gf, ga, gf - ga));
        }

        return standings
            .OrderByDescending(s => s.Points)
            .ThenByDescending(s => s.GoalDifference)
            .ThenByDescending(s => s.GoalsFor);
    }

    public IEnumerable<UnifiedMatch> GetBiggestWins(string? competition = null, int limit = 10)
    {
        var query = _matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m =>
                TeamNameMatcher.IsMatch(m.Competition, competition) ||
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        return query
            .Where(m => m.HomeGoals.HasValue && m.AwayGoals.HasValue)
            .OrderByDescending(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value))
            .ThenByDescending(m => m.Date)
            .Take(limit);
    }

    public double GetAverageGoals(string? competition = null, int? season = null)
    {
        var query = _matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m =>
                TeamNameMatcher.IsMatch(m.Competition, competition) ||
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }
        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        var relevant = query.Where(m => m.TotalGoals.HasValue).ToList();
        if (relevant.Count == 0) return 0.0;
        return relevant.Average(m => m.TotalGoals!.Value);
    }

    public IEnumerable<Player> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int limit = 20)
    {
        var query = _players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            query = query.Where(p =>
                p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            query = query.Where(p =>
                p.Club != null &&
                (p.Club.Contains(club, StringComparison.OrdinalIgnoreCase) ||
                 TeamNameMatcher.IsMatch(p.Club, club)));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            query = query.Where(p =>
                p.Position != null &&
                p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }

        if (minOverall.HasValue)
        {
            query = query.Where(p => p.Overall >= minOverall.Value);
        }

        return query
            .OrderByDescending(p => p.Overall ?? 0)
            .ThenBy(p => p.Name)
            .Take(limit);
    }

    public Player? GetPlayerByName(string name)
    {
        return _players
            .Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .FirstOrDefault();
    }

    public IReadOnlyList<string> ListCompetitions() =>
        _matches.Select(m => m.Competition).Distinct(StringComparer.OrdinalIgnoreCase).ToList();

    private IEnumerable<UnifiedMatch> MatchesForTeam(string team, int? season, string? competition, string? venue)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m =>
                TeamNameMatcher.IsMatch(m.Competition, competition) ||
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
        {
            query = query.Where(m => m.Season == season.Value);
        }

        var homeMatch = string.IsNullOrWhiteSpace(venue) || venue.Equals("home", StringComparison.OrdinalIgnoreCase);
        var awayMatch = string.IsNullOrWhiteSpace(venue) || venue.Equals("away", StringComparison.OrdinalIgnoreCase);

        return query.Where(m =>
            (homeMatch && (TeamNameMatcher.IsMatch(m.HomeTeamBase, team) || TeamNameMatcher.IsMatch(m.HomeTeam, team))) ||
            (awayMatch && (TeamNameMatcher.IsMatch(m.AwayTeamBase, team) || TeamNameMatcher.IsMatch(m.AwayTeam, team))));
    }

    private static bool IsTeamHome(UnifiedMatch match, string team) =>
        TeamNameMatcher.IsMatch(match.HomeTeamBase, team) || TeamNameMatcher.IsMatch(match.HomeTeam, team);
}
