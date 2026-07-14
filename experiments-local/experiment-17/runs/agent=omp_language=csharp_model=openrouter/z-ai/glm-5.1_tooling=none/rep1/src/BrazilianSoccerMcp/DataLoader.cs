using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp;

public class DataLoader
{
    public List<Match> Matches { get; private set; } = [];
    public List<Player> Players { get; private set; } = [];

    /// <summary>Load all CSV data from the given directory.</summary>
    public void Load(string dataDir)
    {
        var kaggleDir = Path.Combine(dataDir, "kaggle");

        var bras = LoadBrasileirao(Path.Combine(kaggleDir, "Brasileirao_Matches.csv"));
        var cup = LoadCopaDoBrasil(Path.Combine(kaggleDir, "Brazilian_Cup_Matches.csv"));
        var lib = LoadLibertadores(Path.Combine(kaggleDir, "Libertadores_Matches.csv"));
        var ext = LoadExtended(Path.Combine(kaggleDir, "BR-Football-Dataset.csv"));
        var hist = LoadHistorical(Path.Combine(kaggleDir, "novo_campeonato_brasileiro.csv"));

        Matches = [.. bras, .. cup, .. lib, .. ext, .. hist];
        Players = LoadPlayers(Path.Combine(kaggleDir, "fifa_data.csv"));
    }

    // ---- Team name normalization ----

    /// <summary>
    /// Normalize a team name for consistent matching.
    /// Removes state suffixes (e.g. "-SP"), strips extra whitespace, and lower-cases for comparison.
    /// </summary>
    public static string NormalizeTeamName(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return "";
        var n = name.Trim();
        // Remove state suffix like "-SP", "-RJ", "-MG", "-RS", "-PR", "-GO", "-BA", "-PE", "-CE", "-SC", "-DF", "-SE", "-PI", "-MA", "-PA", "-TO", "-AC", "-AM", "-AP", "-RR", "-RO", "-ES", "-AL", "-RN", "-PB", "-MS", "-MT", "-BH"
        // Pattern: ends with dash + 2-letter state code
        var idx = n.LastIndexOf('-');
        if (idx > 0 && idx == n.Length - 3)
        {
            var suffix = n[(idx + 1)..];
            if (suffix.Length == 2 && suffix.Equals(suffix, StringComparison.OrdinalIgnoreCase))
                n = n[..idx].Trim();
        }
        return n.Trim();
    }

    /// <summary>Check if two team names refer to the same team after normalization.</summary>
    public static bool SameTeam(string a, string b)
    {
        return string.Equals(NormalizeTeamName(a), NormalizeTeamName(b), StringComparison.OrdinalIgnoreCase);
    }

    // ---- Date parsing helpers ----

    private static DateOnly ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return default;
        s = s.Trim();

        // Handle "2012-05-19 18:30:00" format
        if (s.Length > 10 && s[4] == '-' && s[10] == ' ')
            s = s[..10];

        // Try ISO: yyyy-MM-dd
        if (DateOnly.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
            return d;

        // Try Brazilian: dd/MM/yyyy
        if (DateOnly.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out d))
            return d;

        // Fallback
        if (DateOnly.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out d))
            return d;

        return default;
    }

    private static int ParseInt(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return 0;
        if (int.TryParse(s.Trim(), out var v)) return v;
        return 0;
    }

    // ---- Individual file loaders ----

    private static IEnumerable<Match> LoadBrasileirao(string path)
    {
        if (!File.Exists(path)) yield break;
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null
        });
        foreach (var r in csv.GetRecordsDynamic())
        {
            var dict = (IDictionary<string, object>)r;
            yield return new Match
            {
                Competition = "Brasileirão",
                Date = ParseDate(dict.TryGetValue("datetime", out var dt) ? dt?.ToString() : null),
                HomeTeam = dict.TryGetValue("home_team", out var ht) ? ht?.ToString() ?? "" : "",
                AwayTeam = dict.TryGetValue("away_team", out var at) ? at?.ToString() ?? "" : "",
                HomeGoals = ParseInt(dict.TryGetValue("home_goal", out var hg) ? hg?.ToString() : null),
                AwayGoals = ParseInt(dict.TryGetValue("away_goal", out var ag) ? ag?.ToString() : null),
                Season = ParseInt(dict.TryGetValue("season", out var s) ? s?.ToString() : null),
                Round = dict.TryGetValue("round", out var rd) ? rd?.ToString() ?? "" : "",
                HomeState = dict.TryGetValue("home_team_state", out var hs) ? hs?.ToString() : null,
                AwayState = dict.TryGetValue("away_team_state", out var as2) ? as2?.ToString() : null,
            };
        }
    }

    private static IEnumerable<Match> LoadCopaDoBrasil(string path)
    {
        if (!File.Exists(path)) yield break;
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null
        });
        foreach (var r in csv.GetRecordsDynamic())
        {
            var dict = (IDictionary<string, object>)r;
            yield return new Match
            {
                Competition = "Copa do Brasil",
                Date = ParseDate(dict.TryGetValue("datetime", out var dt) ? dt?.ToString() : null),
                HomeTeam = dict.TryGetValue("home_team", out var ht) ? ht?.ToString() ?? "" : "",
                AwayTeam = dict.TryGetValue("away_team", out var at) ? at?.ToString() ?? "" : "",
                HomeGoals = ParseInt(dict.TryGetValue("home_goal", out var hg) ? hg?.ToString() : null),
                AwayGoals = ParseInt(dict.TryGetValue("away_goal", out var ag) ? ag?.ToString() : null),
                Season = ParseInt(dict.TryGetValue("season", out var s) ? s?.ToString() : null),
                Round = dict.TryGetValue("round", out var rd) ? rd?.ToString() ?? "" : "",
            };
        }
    }

    private static IEnumerable<Match> LoadLibertadores(string path)
    {
        if (!File.Exists(path)) yield break;
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null
        });
        foreach (var r in csv.GetRecordsDynamic())
        {
            var dict = (IDictionary<string, object>)r;
            yield return new Match
            {
                Competition = "Copa Libertadores",
                Date = ParseDate(dict.TryGetValue("datetime", out var dt) ? dt?.ToString() : null),
                HomeTeam = dict.TryGetValue("home_team", out var ht) ? ht?.ToString() ?? "" : "",
                AwayTeam = dict.TryGetValue("away_team", out var at) ? at?.ToString() ??