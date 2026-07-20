using System.Globalization;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads all six Kaggle CSV files into unified in-memory records.
/// </summary>
public static class DataLoader
{
    private static readonly string[] DateFormats =
    [
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy-MM-dd",
        "dd/MM/yyyy HH:mm:ss",
        "dd/MM/yyyy HH:mm",
        "dd/MM/yyyy",
    ];

    public static DateTime? ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim().Trim('"');
        if (DateTime.TryParseExact(s, DateFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var dt))
            return dt;
        // last resort: culture-aware parse (handles a few stragglers)
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return dt;
        return null;
    }

    private static int ParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return 0;
        var s = raw.Trim().Trim('"');
        if (int.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var i)) return i;
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d)) return (int)d;
        return 0;
    }

    private static int? ParseNullableInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim().Trim('"');
        if (int.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var i)) return i;
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d)) return (int)d;
        return null;
    }

    private static Match MakeMatch(string competition, string? dateRaw, int? season,
        string? round, string home, string away, int hg, int ag, string source)
    {
        return new Match
        {
            Competition = competition,
            Date = ParseDate(dateRaw),
            Season = season,
            Round = string.IsNullOrWhiteSpace(round) ? null : round.Trim().Trim('"'),
            HomeTeam = home.Trim().Trim('"'),
            AwayTeam = away.Trim().Trim('"'),
            HomeTeamKey = TeamCanon.CanonicalKey(home),
            AwayTeamKey = TeamCanon.CanonicalKey(away),
            HomeGoals = hg,
            AwayGoals = ag,
            Source = source,
        };
    }

    /// <summary>Loads every match CSV found in <paramref name="dataDir"/>.</summary>
    public static List<Match> LoadMatches(string dataDir)
    {
        var matches = new List<Match>();

        // 1. Brasileirão Série A (2012+)
        var path = Path.Combine(dataDir, "Brasileirao_Matches.csv");
        if (File.Exists(path))
        {
            foreach (var r in CsvReader.ReadRows(path).Skip(1))
            {
                if (r.Length < 9 || string.IsNullOrWhiteSpace(r[1])) continue;
                matches.Add(MakeMatch("Brasileirão Série A", r[0], ParseNullableInt(r[7]),
                    $"Round {ParseInt(r[8])}", r[1], r[3], ParseInt(r[5]), ParseInt(r[6]),
                    "Brasileirao_Matches.csv"));
            }
        }

        // 2. Copa do Brasil
        path = Path.Combine(dataDir, "Brazilian_Cup_Matches.csv");
        if (File.Exists(path))
        {
            foreach (var r in CsvReader.ReadRows(path).Skip(1))
            {
                if (r.Length < 7 || string.IsNullOrWhiteSpace(r[2])) continue;
                matches.Add(MakeMatch("Copa do Brasil", r[1], ParseNullableInt(r[6]),
                    $"Round {ParseInt(r[0])}", r[2], r[3], ParseInt(r[4]), ParseInt(r[5]),
                    "Brazilian_Cup_Matches.csv"));
            }
        }

        // 3. Copa Libertadores
        path = Path.Combine(dataDir, "Libertadores_Matches.csv");
        if (File.Exists(path))
        {
            foreach (var r in CsvReader.ReadRows(path).Skip(1))
            {
                if (r.Length < 7 || string.IsNullOrWhiteSpace(r[1])) continue;
                matches.Add(MakeMatch("Copa Libertadores", r[0], ParseNullableInt(r[5]),
                    r[6], r[1], r[2], ParseInt(r[3]), ParseInt(r[4]),
                    "Libertadores_Matches.csv"));
            }
        }

        // 4. Extended statistics dataset (Serie A/B/C + Copa do Brasil)
        path = Path.Combine(dataDir, "BR-Football-Dataset.csv");
        if (File.Exists(path))
        {
            foreach (var r in CsvReader.ReadRows(path).Skip(1))
            {
                if (r.Length < 13 || string.IsNullOrWhiteSpace(r[1])) continue;
                var tournament = r[0].Trim() switch
                {
                    "Serie A" => "Brasileirão Série A",
                    "Serie B" => "Brasileirão Série B",
                    "Serie C" => "Brasileirão Série C",
                    var t => t,
                };
                var date = ParseDate(r[12]);
                matches.Add(new Match
                {
                    Competition = tournament,
                    Date = date,
                    Season = date?.Year,
                    Round = null,
                    HomeTeam = r[1].Trim(),
                    AwayTeam = r[4].Trim(),
                    HomeTeamKey = TeamCanon.CanonicalKey(r[1]),
                    AwayTeamKey = TeamCanon.CanonicalKey(r[4]),
                    HomeGoals = ParseInt(r[2]),
                    AwayGoals = ParseInt(r[3]),
                    Source = "BR-Football-Dataset.csv",
                });
            }
        }

        // 5. Historical Brasileirão 2003–2019
        path = Path.Combine(dataDir, "novo_campeonato_brasileiro.csv");
        if (File.Exists(path))
        {
            foreach (var r in CsvReader.ReadRows(path).Skip(1))
            {
                if (r.Length < 9 || string.IsNullOrWhiteSpace(r[4])) continue;
                matches.Add(MakeMatch("Brasileirão Série A (histórico)", r[1], ParseNullableInt(r[2]),
                    $"Rodada {ParseInt(r[3])}", r[4], r[5], ParseInt(r[6]), ParseInt(r[7]),
                    "novo_campeonato_brasileiro.csv"));
            }
        }

        return matches;
    }

    /// <summary>Loads FIFA player data (header-driven column lookup).</summary>
    public static List<Player> LoadPlayers(string dataDir)
    {
        var players = new List<Player>();
        var path = Path.Combine(dataDir, "fifa_data.csv");
        if (!File.Exists(path)) return players;

        var rows = CsvReader.ReadRows(path);
        using var e = rows.GetEnumerator();
        if (!e.MoveNext()) return players;

        var header = e.Current;
        var idx = header
            .Select((h, i) => (h: h.Trim(), i))
            .GroupBy(x => x.h)
            .ToDictionary(g => g.Key, g => g.First().i, StringComparer.OrdinalIgnoreCase);

        int Col(string name) => idx.TryGetValue(name, out var i) ? i : -1;
        string? Get(string[] r, int i) => i >= 0 && i < r.Length && !string.IsNullOrWhiteSpace(r[i]) ? r[i].Trim() : null;

        var cId = Col("ID"); var cName = Col("Name"); var cAge = Col("Age");
        var cNat = Col("Nationality"); var cOverall = Col("Overall"); var cPot = Col("Potential");
        var cClub = Col("Club"); var cPos = Col("Position"); var cFoot = Col("Preferred Foot");
        var cJersey = Col("Jersey Number"); var cHeight = Col("Height"); var cWeight = Col("Weight");
        var cCross = Col("Crossing"); var cFin = Col("Finishing"); var cDrib = Col("Dribbling");
        var cPass = Col("ShortPassing"); var cSprint = Col("SprintSpeed");

        while (e.MoveNext())
        {
            var r = e.Current;
            var name = Get(r, cName);
            if (name is null) continue;
            players.Add(new Player
            {
                Id = Get(r, cId) ?? "",
                Name = name,
                Age = ParseNullableInt(Get(r, cAge)),
                Nationality = Get(r, cNat),
                Overall = ParseNullableInt(Get(r, cOverall)),
                Potential = ParseNullableInt(Get(r, cPot)),
                Club = Get(r, cClub),
                Position = Get(r, cPos),
                PreferredFoot = Get(r, cFoot),
                JerseyNumber = ParseNullableInt(Get(r, cJersey)),
                Height = Get(r, cHeight),
                Weight = Get(r, cWeight),
                Crossing = ParseNullableInt(Get(r, cCross)),
                Finishing = ParseNullableInt(Get(r, cFin)),
                Dribbling = ParseNullableInt(Get(r, cDrib)),
                ShortPassing = ParseNullableInt(Get(r, cPass)),
                SprintSpeed = ParseNullableInt(Get(r, cSprint)),
            });
        }

        return players;
    }
}
