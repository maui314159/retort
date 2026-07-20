// Context: Brazilian Soccer MCP Server.
// Loads the six Kaggle CSVs into unified MatchRecord / PlayerRecord lists.
// Handles the three date formats in the wild (ISO with time, ISO date-only,
// Brazilian DD/MM/YYYY), float goal strings from BR-Football-Dataset, and
// deduplicates fixtures that appear in more than one source (same date +
// same canonical teams + same competition) so aggregate stats stay correct.
namespace BrazilianSoccerMcp.Data;

using System.Globalization;

public sealed class SoccerData
{
    public required IReadOnlyList<MatchRecord> Matches { get; init; }
    public required IReadOnlyList<PlayerRecord> Players { get; init; }
    /// <summary>identityKey -> display name, for every team seen in the data.</summary>
    public required IReadOnlyDictionary<string, string> TeamNames { get; init; }

    private static readonly string[] DateFormats =
    [
        "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm", "yyyy-MM-dd", "dd/MM/yyyy", "d/M/yyyy"
    ];

    public static DateOnly ParseDate(string raw)
    {
        raw = raw.Trim().Trim('"');
        if (DateOnly.TryParseExact(raw, DateFormats, CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
            return d;
        if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
            return DateOnly.FromDateTime(dt);
        throw new FormatException($"Unparseable date: '{raw}'");
    }

    private static int ParseGoals(string raw)
    {
        raw = raw.Trim().Trim('"');
        if (int.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out var i)) return i;
        if (double.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out var d)) return (int)Math.Round(d);
        throw new FormatException($"Unparseable goal value: '{raw}'");
    }

    /// <summary>False for "NA"/empty goal cells — unplayed or abandoned matches; callers skip those rows.</summary>
    private static bool TryParseGoals(string raw, out int goals)
    {
        raw = raw.Trim().Trim('"');
        if (int.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out goals)) return true;
        if (double.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
        { goals = (int)Math.Round(d); return true; }
        goals = 0;
        return false;
    }

    /// <summary>Locates the data/kaggle directory: explicit path, env var, cwd, or walk-up search.</summary>
    public static string ResolveDataDir(string? explicitPath = null)
    {
        var candidates = new List<string>();
        if (!string.IsNullOrWhiteSpace(explicitPath)) candidates.Add(explicitPath);
        if (Environment.GetEnvironmentVariable("BRAZILIAN_SOCCER_DATA") is { } env) candidates.Add(env);
        candidates.Add(Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle"));

        foreach (var start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        {
            var dir = new DirectoryInfo(start);
            while (dir is not null)
            {
                candidates.Add(Path.Combine(dir.FullName, "data", "kaggle"));
                dir = dir.Parent;
            }
        }

        foreach (var c in candidates)
            if (Directory.Exists(c) && File.Exists(Path.Combine(c, "Brasileirao_Matches.csv")))
                return Path.GetFullPath(c);
        throw new DirectoryNotFoundException(
            "Could not locate data/kaggle. Set BRAZILIAN_SOCCER_DATA or run from the repository root.");
    }

    public static SoccerData Load(string dataDir)
    {
        var matches = new List<MatchRecord>(capacity: 24_000);
        var seen = new HashSet<string>();
        var teamNames = new Dictionary<string, string>();

        void Register(MatchRecord m)
        {
            // Dedup across overlapping sources; first registration wins
            // (loaders run in priority order: curated files before BR-Football-Dataset).
            if (!seen.Add(m.DedupKey)) return;
            matches.Add(m);
            teamNames.TryAdd(m.HomeTeamKey, TeamNameNormalizer.DisplayFor(m.HomeTeamKey));
            teamNames.TryAdd(m.AwayTeamKey, TeamNameNormalizer.DisplayFor(m.AwayTeamKey));
        }

        LoadBrasileirao(Path.Combine(dataDir, "Brasileirao_Matches.csv"), Register);
        LoadBrazilianCup(Path.Combine(dataDir, "Brazilian_Cup_Matches.csv"), Register);
        LoadLibertadores(Path.Combine(dataDir, "Libertadores_Matches.csv"), Register);
        LoadNovoCampeonato(Path.Combine(dataDir, "novo_campeonato_brasileiro.csv"), Register);
        LoadBrFootball(Path.Combine(dataDir, "BR-Football-Dataset.csv"), Register);

        var players = LoadFifa(Path.Combine(dataDir, "fifa_data.csv"));
        matches.Sort((a, b) => a.Date.CompareTo(b.Date));
        return new SoccerData { Matches = matches, Players = players, TeamNames = teamNames };
    }

    // "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
    private static void LoadBrasileirao(string path, Action<MatchRecord> register)
    {
        foreach (var r in Rows(path))
            register(new MatchRecord
            {
                Date = ParseDate(r["datetime"]),
                HomeTeamRaw = r["home_team"], AwayTeamRaw = r["away_team"],
                HomeTeamKey = TeamNameNormalizer.IdentityKey(r["home_team"]),
                AwayTeamKey = TeamNameNormalizer.IdentityKey(r["away_team"]),
                HomeGoals = ParseGoals(r["home_goal"]), AwayGoals = ParseGoals(r["away_goal"]),
                Competition = Competitions.SerieA,
                Season = int.Parse(r["season"]),
                Round = r["round"],
                Source = "Brasileirao_Matches",
            });
    }

    // "round","datetime","home_team","away_team","home_goal","away_goal","season"
    private static void LoadBrazilianCup(string path, Action<MatchRecord> register)
    {
        foreach (var r in Rows(path))
            register(new MatchRecord
            {
                Date = ParseDate(r["datetime"]),
                HomeTeamRaw = r["home_team"], AwayTeamRaw = r["away_team"],
                HomeTeamKey = TeamNameNormalizer.IdentityKey(r["home_team"]),
                AwayTeamKey = TeamNameNormalizer.IdentityKey(r["away_team"]),
                HomeGoals = ParseGoals(r["home_goal"]), AwayGoals = ParseGoals(r["away_goal"]),
                Competition = Competitions.CopaDoBrasil,
                Season = int.Parse(r["season"]),
                Round = r["round"],
                Source = "Brazilian_Cup_Matches",
            });
    }

    // "datetime","home_team","away_team","home_goal","away_goal","season","stage"
    private static void LoadLibertadores(string path, Action<MatchRecord> register)
    {
        foreach (var r in Rows(path))
            register(new MatchRecord
            {
                Date = ParseDate(r["datetime"]),
                HomeTeamRaw = r["home_team"], AwayTeamRaw = r["away_team"],
                HomeTeamKey = TeamNameNormalizer.IdentityKey(r["home_team"]),
                AwayTeamKey = TeamNameNormalizer.IdentityKey(r["away_team"]),
                HomeGoals = ParseGoals(r["home_goal"]), AwayGoals = ParseGoals(r["away_goal"]),
                Competition = Competitions.Libertadores,
                Season = int.Parse(r["season"]),
                Round = r["stage"],
                Source = "Libertadores_Matches",
            });
    }

    // ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,...,Vencedor,Arena,OBS
    private static void LoadNovoCampeonato(string path, Action<MatchRecord> register)
    {
        foreach (var r in Rows(path))
            register(new MatchRecord
            {
                Date = ParseDate(r["Data"]),
                HomeTeamRaw = r["Equipe_mandante"], AwayTeamRaw = r["Equipe_visitante"],
                HomeTeamKey = TeamNameNormalizer.IdentityKey(r["Equipe_mandante"]),
                AwayTeamKey = TeamNameNormalizer.IdentityKey(r["Equipe_visitante"]),
                HomeGoals = ParseGoals(r["Gols_mandante"]), AwayGoals = ParseGoals(r["Gols_visitante"]),
                Competition = Competitions.SerieA,
                Season = int.Parse(r["Ano"]),
                Round = r["Rodada"],
                Source = "novo_campeonato_brasileiro",
            });
    }

    // tournament,home,home_goal,away_goal,away,...,time,date,...
    private static void LoadBrFootball(string path, Action<MatchRecord> register)
    {
        foreach (var r in Rows(path))
        {
            var competition = Competitions.Normalize(r["tournament"]);
            if (competition is null) continue;
            if (!int.TryParse(r["home_goal"], NumberStyles.Any, CultureInfo.InvariantCulture, out _)
                && !double.TryParse(r["home_goal"], NumberStyles.Any, CultureInfo.InvariantCulture, out _))
                continue; // skip rows without a recorded score
            var date = ParseDate(r["date"]);
            register(new MatchRecord
            {
                Date = date,
                HomeTeamRaw = r["home"], AwayTeamRaw = r["away"],
                HomeTeamKey = TeamNameNormalizer.IdentityKey(r["home"]),
                AwayTeamKey = TeamNameNormalizer.IdentityKey(r["away"]),
                HomeGoals = ParseGoals(r["home_goal"]), AwayGoals = ParseGoals(r["away_goal"]),
                Competition = competition,
                Season = date.Year,
                Round = null,
                Source = "BR-Football-Dataset",
            });
        }
    }

    private static List<PlayerRecord> LoadFifa(string path)
    {
        var players = new List<PlayerRecord>(capacity: 18_500);
        foreach (var r in Rows(path))
        {
            players.Add(new PlayerRecord
            {
                Id = int.TryParse(r.GetValueOrDefault("ID"), out var id) ? id : 0,
                Name = r.GetValueOrDefault("Name") ?? string.Empty,
                Age = ParseInt(r.GetValueOrDefault("Age")),
                Nationality = EmptyToNull(r.GetValueOrDefault("Nationality")),
                Overall = ParseInt(r.GetValueOrDefault("Overall")),
                Potential = ParseInt(r.GetValueOrDefault("Potential")),
                Club = EmptyToNull(r.GetValueOrDefault("Club")),
                Position = EmptyToNull(r.GetValueOrDefault("Position")),
                JerseyNumber = ParseNullableInt(r.GetValueOrDefault("Jersey Number")),
                Height = EmptyToNull(r.GetValueOrDefault("Height")),
                Weight = EmptyToNull(r.GetValueOrDefault("Weight")),
                Finishing = ParseNullableInt(r.GetValueOrDefault("Finishing")),
                Dribbling = ParseNullableInt(r.GetValueOrDefault("Dribbling")),
                ShortPassing = ParseNullableInt(r.GetValueOrDefault("ShortPassing")),
                SprintSpeed = ParseNullableInt(r.GetValueOrDefault("SprintSpeed")),
            });
        }
        return players;
    }

    private static int ParseInt(string? s) =>
        int.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var i) ? i : 0;

    private static int? ParseNullableInt(string? s) =>
        int.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var i) ? i : null;

    private static string? EmptyToNull(string? s) => string.IsNullOrWhiteSpace(s) ? null : s.Trim();

    /// <summary>Yields each data row as a header-name -> value dictionary.</summary>
    private static IEnumerable<Dictionary<string, string>> Rows(string path)
    {
        var rows = CsvParser.ParseFile(path);
        if (rows.Count == 0) yield break;
        var header = rows[0];
        for (var i = 1; i < rows.Count; i++)
        {
            var row = rows[i];
            if (row.Length == 0 || (row.Length == 1 && string.IsNullOrWhiteSpace(row[0]))) continue;
            var dict = new Dictionary<string, string>(header.Length);
            for (var c = 0; c < header.Length; c++)
            {
                var key = header[c];
                if (key.Length == 0) key = $"col{c}";
                dict[key] = c < row.Length ? row[c] : string.Empty;
            }
            yield return dict;
        }
    }
}
