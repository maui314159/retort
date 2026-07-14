using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Services;

public sealed class DataRepository
{
    private readonly string _dataPath;
    private List<Match> _matches = [];
    private List<FifaPlayer> _players = [];
    private bool _loaded;

    public DataRepository(string dataPath)
    {
        _dataPath = dataPath;
    }

    public IReadOnlyList<Match> Matches => _matches;
    public IReadOnlyList<FifaPlayer> Players => _players;

    public async Task LoadAsync(CancellationToken ct = default)
    {
        if (_loaded) return;

        var tasks = new Task<List<Match>>[]
        {
            Task.Run(() => LoadBrasileiraoAsync(), ct),
            Task.Run(() => LoadCopaDoBrasilAsync(), ct),
            Task.Run(() => LoadLibertadoresAsync(), ct),
            Task.Run(() => LoadBrFootballAsync(), ct),
            Task.Run(() => LoadHistoricoAsync(), ct),
        };

        var playerTask = Task.Run(() => LoadFifaPlayersAsync(), ct);

        await Task.WhenAll(tasks.Cast<Task>().Append(playerTask));

        _matches = tasks.SelectMany(t => t.Result).ToList();
        _players = await playerTask;
        _loaded = true;
    }

    // -----------------------------------------------------------------------
    // Query helpers
    // -----------------------------------------------------------------------

    public List<Match> SearchMatches(
        string? team = null,
        string? opponent = null,
        int? season = null,
        Competition? competition = null,
        DateOnly? fromDate = null,
        DateOnly? toDate = null,
        int limit = 50)
    {
        EnsureLoaded();

        return _matches
            .Where(m =>
                (team == null || TeamMatchesQuery(m, team)) &&
                (opponent == null || OpponentMatchesQuery(m, team, opponent)) &&
                (season == null || m.Season == season) &&
                (competition == null || m.Competition == competition) &&
                (fromDate == null || m.Date >= fromDate) &&
                (toDate == null || m.Date <= toDate))
            .OrderByDescending(m => m.Date)
            .Take(limit)
            .ToList();
    }

    private static bool TeamMatchesQuery(Match m, string team) =>
        TeamNameNormalizer.Matches(m.HomeTeam, team) ||
        TeamNameNormalizer.Matches(m.AwayTeam, team);

    private static bool OpponentMatchesQuery(Match m, string? primaryTeam, string opponent)
    {
        // When primary team is specified, check opponent is on the other side
        if (primaryTeam != null)
        {
            bool primaryIsHome = TeamNameNormalizer.Matches(m.HomeTeam, primaryTeam);
            bool primaryIsAway = TeamNameNormalizer.Matches(m.AwayTeam, primaryTeam);
            bool opponentIsHome = TeamNameNormalizer.Matches(m.HomeTeam, opponent);
            bool opponentIsAway = TeamNameNormalizer.Matches(m.AwayTeam, opponent);
            return (primaryIsHome && opponentIsAway) || (primaryIsAway && opponentIsHome);
        }
        return TeamNameNormalizer.Matches(m.HomeTeam, opponent) ||
               TeamNameNormalizer.Matches(m.AwayTeam, opponent);
    }

    public TeamStats GetTeamStats(
        string team,
        int? season = null,
        Competition? competition = null)
    {
        EnsureLoaded();

        var relevant = _matches.Where(m =>
            TeamMatchesQuery(m, team) &&
            (season == null || m.Season == season) &&
            (competition == null || m.Competition == competition));

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in relevant)
        {
            bool isHome = TeamNameNormalizer.Matches(m.HomeTeam, team);
            int scored = isHome ? m.HomeGoals : m.AwayGoals;
            int conceded = isHome ? m.AwayGoals : m.HomeGoals;
            gf += scored;
            ga += conceded;
            if (scored > conceded) wins++;
            else if (scored == conceded) draws++;
            else losses++;
        }

        return new TeamStats(team, wins, draws, losses, gf, ga);
    }

    public List<(TeamStats Stats, string Team)> GetStandings(int season, Competition competition)
    {
        EnsureLoaded();

        var relevant = _matches
            .Where(m => m.Season == season && m.Competition == competition)
            .ToList();

        var teams = relevant
            .SelectMany(m => new[]
            {
                TeamNameNormalizer.Normalize(m.HomeTeam),
                TeamNameNormalizer.Normalize(m.AwayTeam)
            })
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        return teams
            .Select(t => (GetTeamStatsNormalized(t, relevant), t))
            .OrderByDescending(x => x.Item1.Points)
            .ThenByDescending(x => x.Item1.GoalDifference)
            .ThenByDescending(x => x.Item1.GoalsFor)
            .ToList();
    }

    private static TeamStats GetTeamStatsNormalized(string normalizedTeam, List<Match> matches)
    {
        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.Normalize(m.HomeTeam)
                .Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase);
            bool isAway = TeamNameNormalizer.Normalize(m.AwayTeam)
                .Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase);

            if (!isHome && !isAway) continue;

            int scored = isHome ? m.HomeGoals : m.AwayGoals;
            int conceded = isHome ? m.AwayGoals : m.HomeGoals;
            gf += scored;
            ga += conceded;
            if (scored > conceded) wins++;
            else if (scored == conceded) draws++;
            else losses++;
        }
        return new TeamStats(normalizedTeam, wins, draws, losses, gf, ga);
    }

    public List<FifaPlayer> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minRating = null,
        int limit = 20)
    {
        EnsureLoaded();

        return _players
            .Where(p =>
                (name == null || p.Name.Contains(name, StringComparison.OrdinalIgnoreCase)) &&
                (nationality == null || p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase)) &&
                (club == null || p.Club.Contains(club, StringComparison.OrdinalIgnoreCase)) &&
                (position == null || p.Position.Contains(position, StringComparison.OrdinalIgnoreCase)) &&
                (minRating == null || p.Overall >= minRating))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    public List<Match> GetBiggestWins(Competition? competition = null, int limit = 10)
    {
        EnsureLoaded();
        return _matches
            .Where(m => !m.IsDraw && (competition == null || m.Competition == competition))
            .OrderByDescending(m => m.GoalDifference)
            .Take(limit)
            .ToList();
    }

    public (double AvgGoals, double HomeWinRate, double DrawRate, double AwayWinRate, int TotalMatches)
        GetCompetitionStats(Competition? competition = null, int? season = null)
    {
        EnsureLoaded();
        var subset = _matches
            .Where(m =>
                (competition == null || m.Competition == competition) &&
                (season == null || m.Season == season))
            .ToList();

        if (subset.Count == 0)
            return (0, 0, 0, 0, 0);

        int total = subset.Count;
        double avgGoals = subset.Average(m => m.HomeGoals + m.AwayGoals);
        double homeWins = (double)subset.Count(m => m.IsHomeWin) / total * 100;
        double draws = (double)subset.Count(m => m.IsDraw) / total * 100;
        double awayWins = (double)subset.Count(m => m.IsAwayWin) / total * 100;
        return (avgGoals, homeWins, draws, awayWins, total);
    }

    // -----------------------------------------------------------------------
    // CSV loading
    // -----------------------------------------------------------------------

    private List<Match> LoadBrasileiraoAsync()
    {
        var path = Path.Combine(_dataPath, "Brasileirao_Matches.csv");
        if (!File.Exists(path)) return [];

        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture) { HasHeaderRecord = true };
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, cfg);

        var matches = new List<Match>();
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            var date = ParseDate(csv.GetField("datetime"));
            if (!TryParseGoals(csv.GetField("home_goal"), out int hg)) continue;
            if (!TryParseGoals(csv.GetField("away_goal"), out int ag)) continue;
            if (!int.TryParse(csv.GetField("season"), out int season)) continue;

            matches.Add(new Match(
                date,
                csv.GetField("home_team") ?? "",
                csv.GetField("away_team") ?? "",
                hg, ag, season,
                Competition.Brasileirao,
                Round: csv.GetField("round")));
        }
        return matches;
    }

    private List<Match> LoadCopaDoBrasilAsync()
    {
        var path = Path.Combine(_dataPath, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) return [];

        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture) { HasHeaderRecord = true };
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, cfg);

        var matches = new List<Match>();
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            var date = ParseDate(csv.GetField("datetime"));
            if (!TryParseGoals(csv.GetField("home_goal"), out int hg)) continue;
            if (!TryParseGoals(csv.GetField("away_goal"), out int ag)) continue;
            if (!int.TryParse(csv.GetField("season"), out int season)) continue;

            matches.Add(new Match(
                date,
                csv.GetField("home_team") ?? "",
                csv.GetField("away_team") ?? "",
                hg, ag, season,
                Competition.CopaDoBrasil,
                Round: csv.GetField("round")));
        }
        return matches;
    }

    private List<Match> LoadLibertadoresAsync()
    {
        var path = Path.Combine(_dataPath, "Libertadores_Matches.csv");
        if (!File.Exists(path)) return [];

        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture) { HasHeaderRecord = true };
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, cfg);

        var matches = new List<Match>();
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            var date = ParseDate(csv.GetField("datetime"));
            if (!TryParseGoals(csv.GetField("home_goal"), out int hg)) continue;
            if (!TryParseGoals(csv.GetField("away_goal"), out int ag)) continue;
            if (!int.TryParse(csv.GetField("season"), out int season)) continue;

            matches.Add(new Match(
                date,
                csv.GetField("home_team") ?? "",
                csv.GetField("away_team") ?? "",
                hg, ag, season,
                Competition.Libertadores,
                Stage: csv.GetField("stage")));
        }
        return matches;
    }

    private List<Match> LoadBrFootballAsync()
    {
        var path = Path.Combine(_dataPath, "BR-Football-Dataset.csv");
        if (!File.Exists(path)) return [];

        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture) { HasHeaderRecord = true };
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, cfg);

        var matches = new List<Match>();
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            var rawDate = csv.GetField("date") ?? "";
            var date = ParseDate(rawDate);
            if (!TryParseGoals(csv.GetField("home_goal"), out int hg)) continue;
            if (!TryParseGoals(csv.GetField("away_goal"), out int ag)) continue;

            var season = date.Year;
            matches.Add(new Match(
                date,
                csv.GetField("home") ?? "",
                csv.GetField("away") ?? "",
                hg, ag, season,
                Competition.BrFootball,
                Stage: csv.GetField("tournament")));
        }
        return matches;
    }

    private List<Match> LoadHistoricoAsync()
    {
        var path = Path.Combine(_dataPath, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) return [];

        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture) { HasHeaderRecord = true };
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, cfg);

        var matches = new List<Match>();
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            // Date format: DD/MM/YYYY
            var rawDate = csv.GetField("Data") ?? "";
            var date = ParseDate(rawDate);
            if (!TryParseGoals(csv.GetField("Gols_mandante"), out int hg)) continue;
            if (!TryParseGoals(csv.GetField("Gols_visitante"), out int ag)) continue;
            if (!int.TryParse(csv.GetField("Ano"), out int season)) continue;

            matches.Add(new Match(
                date,
                csv.GetField("Equipe_mandante") ?? "",
                csv.GetField("Equipe_visitante") ?? "",
                hg, ag, season,
                Competition.HistoricoBrasileiro,
                Round: csv.GetField("Rodada"),
                Stadium: csv.GetField("Arena")));
        }
        return matches;
    }

    private List<FifaPlayer> LoadFifaPlayersAsync()
    {
        var path = Path.Combine(_dataPath, "fifa_data.csv");
        if (!File.Exists(path)) return [];

        // BOM-aware reader
        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture) { HasHeaderRecord = true };
        using var reader = new StreamReader(path, detectEncodingFromByteOrderMarks: true);
        using var csv = new CsvReader(reader, cfg);

        csv.Read(); csv.ReadHeader();

        // The CSV has a leading BOM column (empty header) followed by real columns.
        // We read by header name, so we just access the columns we care about.
        var players = new List<FifaPlayer>();
        while (csv.Read())
        {
            if (!int.TryParse(csv.GetField("ID"), out int id)) continue;
            if (!int.TryParse(csv.GetField("Overall"), out int overall)) continue;
            if (!int.TryParse(csv.GetField("Potential"), out int potential)) continue;
            if (!int.TryParse(csv.GetField("Age"), out int age)) continue;

            players.Add(new FifaPlayer(
                id,
                csv.GetField("Name") ?? "",
                age,
                csv.GetField("Nationality") ?? "",
                overall,
                potential,
                csv.GetField("Club") ?? "",
                csv.GetField("Position") ?? "",
                csv.GetField("Jersey Number") ?? "",
                csv.GetField("Height") ?? "",
                csv.GetField("Weight") ?? ""));
        }
        return players;
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private void EnsureLoaded()
    {
        if (!_loaded)
            throw new InvalidOperationException("Data not loaded. Call LoadAsync() first.");
    }

    private static DateOnly ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return DateOnly.MinValue;

        raw = raw.Trim();

        // ISO with time: "2012-05-19 18:30:00"
        if (raw.Length > 10 && raw[10] == ' ')
            raw = raw[..10];

        // ISO: "2023-09-24"
        if (DateOnly.TryParseExact(raw, "yyyy-MM-dd", null, DateTimeStyles.None, out var iso))
            return iso;

        // Brazilian: "29/03/2003"
        if (DateOnly.TryParseExact(raw, "dd/MM/yyyy", null, DateTimeStyles.None, out var br))
            return br;

        return DateOnly.MinValue;
    }

    private static bool TryParseGoals(string? raw, out int goals)
    {
        goals = 0;
        if (string.IsNullOrWhiteSpace(raw)) return false;
        raw = raw.Trim().TrimEnd('.', '0');
        if (raw.EndsWith('.')) raw = raw[..^1];
        if (string.IsNullOrEmpty(raw)) raw = "0";
        return int.TryParse(raw, out goals);
    }
}
