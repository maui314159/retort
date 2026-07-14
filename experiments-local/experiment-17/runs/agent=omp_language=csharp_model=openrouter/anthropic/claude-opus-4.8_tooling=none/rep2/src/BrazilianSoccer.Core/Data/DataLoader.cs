// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    DataLoader.cs
// Project: BrazilianSoccer.Core
// Purpose: Load every provided Kaggle CSV into the unified Match/Player models.
//          Each source file has a distinct schema, column naming and date
//          format; this loader maps all of them onto the common shape and is
//          the single ingestion point for the query layer.
// Handles:
//   - Brasileirao_Matches.csv  (state-suffixed names, ISO datetime)
//   - Brazilian_Cup_Matches.csv (Copa do Brasil)
//   - Libertadores_Matches.csv  (quoted numeric goals, stage column)
//   - BR-Football-Dataset.csv   (tournament column, decimal goals, date+time)
//   - novo_campeonato_brasileiro.csv (Portuguese headers, DD/MM/YYYY dates)
//   - fifa_data.csv             (wide player schema, UTF-8 BOM)
// Robustness: rows with unparseable goals are skipped rather than throwing, so
//             one malformed line never aborts a load.
// =============================================================================

using System.Globalization;
using BrazilianSoccer.Core.Csv;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Data;

/// <summary>The in-memory dataset: all matches and all players.</summary>
public sealed class SoccerDataset
{
    public required IReadOnlyList<Match> Matches { get; init; }
    public required IReadOnlyList<Player> Players { get; init; }
}

/// <summary>Loads the Kaggle CSV files into a <see cref="SoccerDataset"/>.</summary>
public sealed class DataLoader
{
    private readonly string _dataDirectory;

    private static readonly string[] DateFormats =
    [
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "yyyy.MM.dd",
        "MM/dd/yyyy",
    ];

    public DataLoader(string dataDirectory) => _dataDirectory = dataDirectory;

    /// <summary>
    /// Finds the bundled <c>data/kaggle</c> directory by walking up from the
    /// current/base directory. Used so the server and tests locate data
    /// without an absolute path.
    /// </summary>
    public static string LocateDataDirectory()
    {
        foreach (var start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        {
            var dir = new DirectoryInfo(start);
            while (dir is not null)
            {
                var candidate = Path.Combine(dir.FullName, "data", "kaggle");
                if (Directory.Exists(candidate))
                    return candidate;
                dir = dir.Parent;
            }
        }
        throw new DirectoryNotFoundException(
            "Could not locate the 'data/kaggle' directory. Set the data path explicitly.");
    }

    // Relative authority of each source file. The same Brasileirão/Copa do
    // Brasil seasons appear in several files with slightly different team-name
    // spellings and timestamps, so row-level de-duplication is unreliable.
    // Instead, for each (competition, season) slice we keep only the rows from
    // the single most authoritative source that covers it. Lower = preferred.
    private static readonly Dictionary<string, int> SourcePriority = new(StringComparer.Ordinal)
    {
        ["Brasileirao_Matches.csv"] = 0,
        ["Brazilian_Cup_Matches.csv"] = 0,
        ["Libertadores_Matches.csv"] = 0,
        ["novo_campeonato_brasileiro.csv"] = 1,
        ["BR-Football-Dataset.csv"] = 2,
    };

    public SoccerDataset Load()
    {
        var raw = new List<Match>();
        raw.AddRange(LoadBrasileirao());
        raw.AddRange(LoadCopaDoBrasil());
        raw.AddRange(LoadLibertadores());
        raw.AddRange(LoadHistorical());
        raw.AddRange(LoadExtended());

        var matches = SelectAuthoritativeSource(raw);
        var players = LoadPlayers().ToList();

        return new SoccerDataset { Matches = matches, Players = players };
    }

    // For each (competition, season) keep only rows from the lowest-priority
    // (most authoritative) source present for that slice. Slices with no season
    // are passed through unchanged.
    private static List<Match> SelectAuthoritativeSource(List<Match> matches)
    {
        var bestPriority = new Dictionary<(Competition, int), int>();
        foreach (var m in matches)
        {
            if (m.Season is not { } season)
                continue;
            var pri = SourcePriority.GetValueOrDefault(m.Source, int.MaxValue);
            var key = (m.Competition, season);
            if (!bestPriority.TryGetValue(key, out var cur) || pri < cur)
                bestPriority[key] = pri;
        }

        var result = new List<Match>(matches.Count);
        foreach (var m in matches)
        {
            if (m.Season is not { } season)
            {
                result.Add(m);
                continue;
            }
            var pri = SourcePriority.GetValueOrDefault(m.Source, int.MaxValue);
            if (pri == bestPriority[(m.Competition, season)])
                result.Add(m);
        }
        return result;
    }

    private string Path_(string file) => Path.Combine(_dataDirectory, file);

    private IEnumerable<Match> LoadBrasileirao()
    {
        var path = Path_("Brasileirao_Matches.csv");
        if (!File.Exists(path)) yield break;

        foreach (var row in CsvReader.ReadFile(path))
        {
            if (!TryGoal(row, "home_goal", out var hg) || !TryGoal(row, "away_goal", out var ag))
                continue;
            var home = row.GetValueOrDefault("home_team", "");
            var away = row.GetValueOrDefault("away_team", "");
            yield return new Match
            {
                HomeTeam = TeamNameNormalizer.Display(home),
                AwayTeam = TeamNameNormalizer.Display(away),
                HomeTeamKey = TeamNameNormalizer.Canonical(home),
                AwayTeamKey = TeamNameNormalizer.Canonical(away),
                HomeGoals = hg,
                AwayGoals = ag,
                Date = ParseDate(row.GetValueOrDefault("datetime", "")),
                Season = ParseInt(row.GetValueOrDefault("season", "")),
                Round = NullIfEmpty(row.GetValueOrDefault("round", "")),
                Competition = Competition.Brasileirao,
                Source = "Brasileirao_Matches.csv",
            };
        }
    }

    private IEnumerable<Match> LoadCopaDoBrasil()
    {
        var path = Path_("Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) yield break;

        foreach (var row in CsvReader.ReadFile(path))
        {
            if (!TryGoal(row, "home_goal", out var hg) || !TryGoal(row, "away_goal", out var ag))
                continue;
            var home = row.GetValueOrDefault("home_team", "");
            var away = row.GetValueOrDefault("away_team", "");
            yield return new Match
            {
                HomeTeam = TeamNameNormalizer.Display(home),
                AwayTeam = TeamNameNormalizer.Display(away),
                HomeTeamKey = TeamNameNormalizer.Canonical(home),
                AwayTeamKey = TeamNameNormalizer.Canonical(away),
                HomeGoals = hg,
                AwayGoals = ag,
                Date = ParseDate(row.GetValueOrDefault("datetime", "")),
                Season = ParseInt(row.GetValueOrDefault("season", "")),
                Round = NullIfEmpty(row.GetValueOrDefault("round", "")),
                Competition = Competition.CopaDoBrasil,
                Source = "Brazilian_Cup_Matches.csv",
            };
        }
    }

    private IEnumerable<Match> LoadLibertadores()
    {
        var path = Path_("Libertadores_Matches.csv");
        if (!File.Exists(path)) yield break;

        foreach (var row in CsvReader.ReadFile(path))
        {
            if (!TryGoal(row, "home_goal", out var hg) || !TryGoal(row, "away_goal", out var ag))
                continue;
            var home = row.GetValueOrDefault("home_team", "");
            var away = row.GetValueOrDefault("away_team", "");
            yield return new Match
            {
                HomeTeam = TeamNameNormalizer.Display(home),
                AwayTeam = TeamNameNormalizer.Display(away),
                HomeTeamKey = TeamNameNormalizer.Canonical(home),
                AwayTeamKey = TeamNameNormalizer.Canonical(away),
                HomeGoals = hg,
                AwayGoals = ag,
                Date = ParseDate(row.GetValueOrDefault("datetime", "")),
                Season = ParseInt(row.GetValueOrDefault("season", "")),
                Stage = NullIfEmpty(row.GetValueOrDefault("stage", "")),
                Competition = Competition.Libertadores,
                Source = "Libertadores_Matches.csv",
            };
        }
    }

    private IEnumerable<Match> LoadExtended()
    {
        var path = Path_("BR-Football-Dataset.csv");
        if (!File.Exists(path)) yield break;

        foreach (var row in CsvReader.ReadFile(path))
        {
            if (!TryGoal(row, "home_goal", out var hg) || !TryGoal(row, "away_goal", out var ag))
                continue;
            var home = row.GetValueOrDefault("home", "");
            var away = row.GetValueOrDefault("away", "");
            var tournament = row.GetValueOrDefault("tournament", "");
            var date = ParseDate(row.GetValueOrDefault("date", ""));
            yield return new Match
            {
                HomeTeam = TeamNameNormalizer.Display(home),
                AwayTeam = TeamNameNormalizer.Display(away),
                HomeTeamKey = TeamNameNormalizer.Canonical(home),
                AwayTeamKey = TeamNameNormalizer.Canonical(away),
                HomeGoals = hg,
                AwayGoals = ag,
                Date = date,
                Season = date?.Year,
                Stage = NullIfEmpty(tournament),
                Competition = ClassifyTournament(tournament),
                Source = "BR-Football-Dataset.csv",
            };
        }
    }

    private IEnumerable<Match> LoadHistorical()
    {
        var path = Path_("novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) yield break;

        foreach (var row in CsvReader.ReadFile(path))
        {
            if (!TryGoal(row, "Gols_mandante", out var hg) || !TryGoal(row, "Gols_visitante", out var ag))
                continue;
            var home = row.GetValueOrDefault("Equipe_mandante", "");
            var away = row.GetValueOrDefault("Equipe_visitante", "");
            yield return new Match
            {
                HomeTeam = TeamNameNormalizer.Display(home),
                AwayTeam = TeamNameNormalizer.Display(away),
                HomeTeamKey = TeamNameNormalizer.Canonical(home),
                AwayTeamKey = TeamNameNormalizer.Canonical(away),
                HomeGoals = hg,
                AwayGoals = ag,
                Date = ParseDate(row.GetValueOrDefault("Data", "")),
                Season = ParseInt(row.GetValueOrDefault("Ano", "")),
                Round = NullIfEmpty(row.GetValueOrDefault("Rodada", "")),
                Arena = NullIfEmpty(row.GetValueOrDefault("Arena", "")),
                Competition = Competition.Brasileirao,
                Source = "novo_campeonato_brasileiro.csv",
            };
        }
    }

    private IEnumerable<Player> LoadPlayers()
    {
        var path = Path_("fifa_data.csv");
        if (!File.Exists(path)) yield break;

        foreach (var row in CsvReader.ReadFile(path))
        {
            var name = row.GetValueOrDefault("Name", "");
            if (string.IsNullOrWhiteSpace(name))
                continue;
            var club = row.GetValueOrDefault("Club", "");
            yield return new Player
            {
                Id = ParseInt(row.GetValueOrDefault("ID", "")) ?? 0,
                Name = name.Trim(),
                Age = ParseInt(row.GetValueOrDefault("Age", "")) ?? 0,
                Nationality = row.GetValueOrDefault("Nationality", "").Trim(),
                Overall = ParseInt(row.GetValueOrDefault("Overall", "")) ?? 0,
                Potential = ParseInt(row.GetValueOrDefault("Potential", "")) ?? 0,
                Club = club.Trim(),
                ClubKey = TeamNameNormalizer.Canonical(club),
                Position = row.GetValueOrDefault("Position", "").Trim(),
                JerseyNumber = ParseInt(row.GetValueOrDefault("Jersey Number", "")),
                Height = row.GetValueOrDefault("Height", "").Trim(),
                Weight = row.GetValueOrDefault("Weight", "").Trim(),
                PreferredFoot = row.GetValueOrDefault("Preferred Foot", "").Trim(),
            };
        }
    }

    private static Competition ClassifyTournament(string tournament)
    {
        var t = tournament.Trim();
        if (t.Equals("Copa do Brasil", StringComparison.OrdinalIgnoreCase))
            return Competition.CopaDoBrasil;
        if (t.StartsWith("Serie A", StringComparison.OrdinalIgnoreCase))
            return Competition.Brasileirao;
        if (t.Contains("Libertadores", StringComparison.OrdinalIgnoreCase))
            return Competition.Libertadores;
        return Competition.Other;
    }

    // Goals may be unquoted ("1"), quoted ("2") or decimal ("1.0"); empty/NaN -> skip.
    private static bool TryGoal(IReadOnlyDictionary<string, string> row, string key, out int value)
    {
        value = 0;
        var raw = row.GetValueOrDefault(key, "").Trim();
        if (raw.Length == 0)
            return false;
        if (int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            return true;
        if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var d) && !double.IsNaN(d))
        {
            value = (int)Math.Round(d);
            return true;
        }
        return false;
    }

    private static int? ParseInt(string raw)
    {
        raw = raw.Trim();
        if (int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;
        if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var d) && !double.IsNaN(d))
            return (int)Math.Round(d);
        return null;
    }

    private static DateTime? ParseDate(string raw)
    {
        raw = raw.Trim();
        if (raw.Length == 0)
            return null;
        if (DateTime.TryParseExact(raw, DateFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var dt))
            return dt;
        if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return dt;
        return null;
    }

    private static string? NullIfEmpty(string value)
        => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
}
