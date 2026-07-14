// =============================================================================
// File:    DataLoader.cs
// Project: BrazilianSoccer.Core
// Purpose: Parse each of the six Kaggle CSV files into the unified Match /
//          Player domain model. One loader method per file shape; each maps
//          source columns by header name (order-independent), normalizes team
//          names (NameNormalizer) and parses the source-specific date format.
// Context: Files differ in columns, quoting and date formats (see TASK.md
//          "Data Quality Notes"):
//            - Brasileirao_Matches.csv  : ISO datetime, "Team-UF" suffixes.
//            - Brazilian_Cup_Matches.csv: ISO datetime, "Name - UF" suffixes.
//            - Libertadores_Matches.csv : ISO datetime, goals quoted, stage col.
//            - BR-Football-Dataset.csv  : "tournament" maps to Serie A/B/C or
//                                         Copa do Brasil; date-only; has shots
//                                         and corners.
//            - novo_campeonato_brasileiro.csv: DD/MM/YYYY date, Portuguese cols.
//            - fifa_data.csv            : player rows, BOM on first cell.
//          Parsing is defensive: rows with unparseable goals keep null scores
//          rather than throwing, so a few dirty rows never abort a load.
// =============================================================================

using System.Globalization;

namespace BrazilianSoccer.Core;

public static class DataLoader
{
    /// <summary>Loads every dataset under <paramref name="dataDir"/> into one dataset.</summary>
    public static SoccerDataset LoadAll(string dataDir)
    {
        var matches = new List<Match>();
        var players = new List<Player>();

        void TryLoad(string file, Action<string, List<Match>> loader)
        {
            var path = Path.Combine(dataDir, file);
            if (File.Exists(path)) loader(path, matches);
        }

        TryLoad("Brasileirao_Matches.csv", LoadBrasileirao);
        TryLoad("Brazilian_Cup_Matches.csv", LoadCopaDoBrasil);
        TryLoad("Libertadores_Matches.csv", LoadLibertadores);
        TryLoad("BR-Football-Dataset.csv", LoadBrFootball);
        TryLoad("novo_campeonato_brasileiro.csv", LoadHistorical);

        var fifaPath = Path.Combine(dataDir, "fifa_data.csv");
        if (File.Exists(fifaPath)) LoadFifa(fifaPath, players);

        return new SoccerDataset(Deduplicate(matches), players);
    }

    // Several sources overlap: Série A appears in Brasileirao_Matches.csv,
    // novo_campeonato_brasileiro.csv AND BR-Football-Dataset.csv, which would
    // triple-count results. Sources disagree on the exact kickoff date (±1 day
    // timezone drift) so the date cannot anchor a fixture key. In a round-robin
    // league each ordered pairing (home vs away) occurs once per season, so
    // (competition, season, homeKey, awayKey) identifies the fixture; two-leg
    // cup ties swap home/away and therefore keep distinct keys. We only collapse
    // rows that come from DIFFERENT source files, merging non-null fields so the
    // survivor keeps round, venue and extended stats from whichever source had
    // them; identical fixtures within one file (none expected) are left intact.
    private static List<Match> Deduplicate(List<Match> matches)
    {
        var primary = new Dictionary<string, int>(StringComparer.Ordinal);
        var sources = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
        var result = new List<Match>(matches.Count);

        foreach (var m in matches)
        {
            var key = $"{(int)m.Competition}|{m.Season}|{m.HomeKey}|{m.AwayKey}";

            if (primary.TryGetValue(key, out var idx) && sources[key].Add(m.Source))
            {
                result[idx] = Merge(result[idx], m);
            }
            else if (!primary.ContainsKey(key))
            {
                primary[key] = result.Count;
                sources[key] = new HashSet<string>(StringComparer.Ordinal) { m.Source };
                result.Add(m);
            }
            else
            {
                // Same fixture key already seen from this same source: a genuine
                // separate row (or a within-file repeat); keep it as its own match.
                result.Add(m);
            }
        }
        return result;
    }

    private static Match Merge(Match keep, Match extra) => keep with
    {
        HomeGoals = keep.HomeGoals ?? extra.HomeGoals,
        AwayGoals = keep.AwayGoals ?? extra.AwayGoals,
        Round = keep.Round ?? extra.Round,
        Stage = keep.Stage ?? extra.Stage,
        Venue = keep.Venue ?? extra.Venue,
        HomeShots = keep.HomeShots ?? extra.HomeShots,
        AwayShots = keep.AwayShots ?? extra.AwayShots,
        HomeCorners = keep.HomeCorners ?? extra.HomeCorners,
        AwayCorners = keep.AwayCorners ?? extra.AwayCorners,
    };

    // --- Match loaders -------------------------------------------------------

    private static void LoadBrasileirao(string path, List<Match> sink)
    {
        foreach (var (cells, col) in Rows(path))
        {
            string home = Get(cells, col, "home_team");
            string away = Get(cells, col, "away_team");
            if (home.Length == 0 || away.Length == 0) continue;

            sink.Add(BuildMatch(
                Competition.BrasileiraoSerieA, "Brasileirao_Matches.csv",
                home, away,
                ParseInt(Get(cells, col, "home_goal")),
                ParseInt(Get(cells, col, "away_goal")),
                ParseDate(Get(cells, col, "datetime")),
                season: ParseInt(Get(cells, col, "season")) ?? 0,
                round: Get(cells, col, "round")));
        }
    }

    private static void LoadCopaDoBrasil(string path, List<Match> sink)
    {
        foreach (var (cells, col) in Rows(path))
        {
            string home = Get(cells, col, "home_team");
            string away = Get(cells, col, "away_team");
            if (home.Length == 0 || away.Length == 0) continue;

            sink.Add(BuildMatch(
                Competition.CopaDoBrasil, "Brazilian_Cup_Matches.csv",
                home, away,
                ParseInt(Get(cells, col, "home_goal")),
                ParseInt(Get(cells, col, "away_goal")),
                ParseDate(Get(cells, col, "datetime")),
                season: ParseInt(Get(cells, col, "season")) ?? 0,
                round: Get(cells, col, "round")));
        }
    }

    private static void LoadLibertadores(string path, List<Match> sink)
    {
        foreach (var (cells, col) in Rows(path))
        {
            string home = Get(cells, col, "home_team");
            string away = Get(cells, col, "away_team");
            if (home.Length == 0 || away.Length == 0) continue;

            sink.Add(BuildMatch(
                Competition.Libertadores, "Libertadores_Matches.csv",
                home, away,
                ParseInt(Get(cells, col, "home_goal")),
                ParseInt(Get(cells, col, "away_goal")),
                ParseDate(Get(cells, col, "datetime")),
                season: ParseInt(Get(cells, col, "season")) ?? 0,
                stage: Get(cells, col, "stage")));
        }
    }

    private static void LoadBrFootball(string path, List<Match> sink)
    {
        foreach (var (cells, col) in Rows(path))
        {
            string home = Get(cells, col, "home");
            string away = Get(cells, col, "away");
            if (home.Length == 0 || away.Length == 0) continue;

            var date = ParseDate(Get(cells, col, "date"));
            sink.Add(BuildMatch(
                MapTournament(Get(cells, col, "tournament")), "BR-Football-Dataset.csv",
                home, away,
                ParseInt(Get(cells, col, "home_goal")),
                ParseInt(Get(cells, col, "away_goal")),
                date,
                season: date?.Year ?? 0,
                homeShots: ParseInt(Get(cells, col, "home_shots")),
                awayShots: ParseInt(Get(cells, col, "away_shots")),
                homeCorners: ParseInt(Get(cells, col, "home_corner")),
                awayCorners: ParseInt(Get(cells, col, "away_corner"))));
        }
    }

    private static void LoadHistorical(string path, List<Match> sink)
    {
        foreach (var (cells, col) in Rows(path))
        {
            string home = Get(cells, col, "Equipe_mandante");
            string away = Get(cells, col, "Equipe_visitante");
            if (home.Length == 0 || away.Length == 0) continue;

            sink.Add(BuildMatch(
                Competition.BrasileiraoSerieA, "novo_campeonato_brasileiro.csv",
                home, away,
                ParseInt(Get(cells, col, "Gols_mandante")),
                ParseInt(Get(cells, col, "Gols_visitante")),
                ParseDate(Get(cells, col, "Data")),
                season: ParseInt(Get(cells, col, "Ano")) ?? 0,
                round: Get(cells, col, "Rodada"),
                venue: Get(cells, col, "Arena")));
        }
    }

    private static void LoadFifa(string path, List<Player> sink)
    {
        foreach (var (cells, col) in Rows(path))
        {
            string name = Get(cells, col, "Name");
            if (name.Length == 0) continue;

            string club = Get(cells, col, "Club");
            sink.Add(new Player
            {
                Id = ParseInt(Get(cells, col, "ID")) ?? 0,
                Name = name,
                Age = ParseInt(Get(cells, col, "Age")),
                Nationality = Get(cells, col, "Nationality"),
                Overall = ParseInt(Get(cells, col, "Overall")) ?? 0,
                Potential = ParseInt(Get(cells, col, "Potential")) ?? 0,
                Club = club,
                Position = Get(cells, col, "Position"),
                JerseyNumber = ParseInt(Get(cells, col, "Jersey Number")),
                Height = Get(cells, col, "Height"),
                Weight = Get(cells, col, "Weight"),
                ClubKey = NameNormalizer.Key(club),
                NameKey = NameNormalizer.Key(name),
            });
        }
    }

    // --- Helpers -------------------------------------------------------------

    private static IEnumerable<(string[] cells, Dictionary<string, int> col)> Rows(string path)
    {
        Dictionary<string, int>? col = null;
        foreach (var cells in Csv.ReadRecords(path))
        {
            if (col is null) { col = Csv.HeaderIndex(cells); continue; }
            yield return (cells, col);
        }
    }

    private static Match BuildMatch(
        Competition competition, string source,
        string home, string away, int? homeGoals, int? awayGoals,
        DateTime? date, int season,
        string? round = null, string? stage = null, string? venue = null,
        int? homeShots = null, int? awayShots = null,
        int? homeCorners = null, int? awayCorners = null)
    {
        return new Match
        {
            Competition = competition,
            Source = source,
            HomeTeam = NameNormalizer.Display(home),
            AwayTeam = NameNormalizer.Display(away),
            HomeKey = NameNormalizer.Key(home),
            AwayKey = NameNormalizer.Key(away),
            HomeGoals = homeGoals,
            AwayGoals = awayGoals,
            Date = date,
            Season = season,
            Round = Clean(round),
            Stage = Clean(stage),
            Venue = Clean(venue),
            HomeShots = homeShots,
            AwayShots = awayShots,
            HomeCorners = homeCorners,
            AwayCorners = awayCorners,
        };
    }

    private static Competition MapTournament(string t)
    {
        var k = t.Trim().ToLowerInvariant();
        return k switch
        {
            "serie a" => Competition.BrasileiraoSerieA,
            "serie b" => Competition.BrasileiraoSerieB,
            "serie c" => Competition.BrasileiraoSerieC,
            "copa do brasil" => Competition.CopaDoBrasil,
            _ => Competition.Unknown,
        };
    }

    private static string Get(string[] cells, Dictionary<string, int> col, string name)
        => col.TryGetValue(name, out var i) && i < cells.Length ? cells[i].Trim() : "";

    private static string? Clean(string? s) => string.IsNullOrWhiteSpace(s) ? null : s.Trim();

    private static int? ParseInt(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        s = s.Trim();
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;
        // Tolerate decimal-formatted ints like "2.0" from BR-Football-Dataset.csv.
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)Math.Round(d);
        return null;
    }

    private static readonly string[] DateFormats =
    {
        "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd", "dd/MM/yyyy",
        "dd/MM/yyyy HH:mm:ss", "yyyy.MM.dd",
    };

    private static DateTime? ParseDate(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        s = s.Trim();
        if (DateTime.TryParseExact(s, DateFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var dt))
            return dt;
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return dt;
        return null;
    }
}
