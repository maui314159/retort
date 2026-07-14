using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Loads each of the six Kaggle CSV files into <see cref="MatchRecord"/> /
/// <see cref="FifaPlayer"/> lists.
/// </summary>
public static class CsvLoaders
{
    // ─── helpers ──────────────────────────────────────────────────────────────

    private static CsvConfiguration Cfg(bool hasHeader = true) => new(CultureInfo.InvariantCulture)
    {
        HasHeaderRecord = hasHeader,
        MissingFieldFound = null,          // tolerate sparse rows
        BadDataFound = null,               // skip malformed cells
        TrimOptions = TrimOptions.Trim,
    };

    private static DateTime ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return DateTime.MinValue;
        raw = raw.Trim('"').Trim();

        // Try common formats
        string[] formats =
        [
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd",
            "dd/MM/yyyy",
            "M/d/yyyy",
        ];
        if (DateTime.TryParseExact(raw, formats, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var dt)) return dt;
        if (DateTime.TryParse(raw, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out dt)) return dt;
        return DateTime.MinValue;
    }

    private static int ParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return 0;
        raw = raw.Trim('"').Trim();
        return int.TryParse(raw.Split('.')[0], out var v) ? v : 0;
    }

    private static MatchRecord MakeRecord(
        DateTime date, string home, string away,
        int homeGoals, int awayGoals,
        string competition, int season, string round, string? arena = null) =>
        new()
        {
            Date           = date,
            HomeTeam       = home,
            AwayTeam       = away,
            HomeGoals      = homeGoals,
            AwayGoals      = awayGoals,
            Competition    = competition,
            Season         = season,
            Round          = round,
            Arena          = arena,
            HomeTeamKey        = TeamNameNormalizer.Normalize(home),
            AwayTeamKey        = TeamNameNormalizer.Normalize(away),
            HomeTeamSearchKey  = TeamNameNormalizer.NormalizeForSearch(home),
            AwayTeamSearchKey  = TeamNameNormalizer.NormalizeForSearch(away),
        };

    // ─── Brasileirao_Matches.csv ──────────────────────────────────────────────

    public static List<MatchRecord> LoadBrasileirao(string path)
    {
        var results = new List<MatchRecord>();
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Cfg());
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                results.Add(MakeRecord(
                    date:        ParseDate(csv.GetField("datetime")),
                    home:        csv.GetField("home_team") ?? "",
                    away:        csv.GetField("away_team") ?? "",
                    homeGoals:   ParseInt(csv.GetField("home_goal")),
                    awayGoals:   ParseInt(csv.GetField("away_goal")),
                    competition: "Brasileirao",
                    season:      ParseInt(csv.GetField("season")),
                    round:       csv.GetField("round") ?? ""));
            }
            catch { /* skip malformed row */ }
        }
        return results;
    }

    // ─── Brazilian_Cup_Matches.csv ────────────────────────────────────────────

    public static List<MatchRecord> LoadCopaDoBrasil(string path)
    {
        var results = new List<MatchRecord>();
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Cfg());
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                results.Add(MakeRecord(
                    date:        ParseDate(csv.GetField("datetime")),
                    home:        csv.GetField("home_team") ?? "",
                    away:        csv.GetField("away_team") ?? "",
                    homeGoals:   ParseInt(csv.GetField("home_goal")),
                    awayGoals:   ParseInt(csv.GetField("away_goal")),
                    competition: "Copa do Brasil",
                    season:      ParseInt(csv.GetField("season")),
                    round:       csv.GetField("round") ?? ""));
            }
            catch { /* skip */ }
        }
        return results;
    }

    // ─── Libertadores_Matches.csv ─────────────────────────────────────────────

    public static List<MatchRecord> LoadLibertadores(string path)
    {
        var results = new List<MatchRecord>();
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Cfg());
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                var stage = csv.GetField("stage") ?? "";
                results.Add(MakeRecord(
                    date:        ParseDate(csv.GetField("datetime")),
                    home:        csv.GetField("home_team") ?? "",
                    away:        csv.GetField("away_team") ?? "",
                    homeGoals:   ParseInt(csv.GetField("home_goal")),
                    awayGoals:   ParseInt(csv.GetField("away_goal")),
                    competition: "Copa Libertadores",
                    season:      ParseInt(csv.GetField("season")),
                    round:       stage));
            }
            catch { /* skip */ }
        }
        return results;
    }

    // ─── BR-Football-Dataset.csv ──────────────────────────────────────────────

    public static List<MatchRecord> LoadBrFootball(string path)
    {
        var results = new List<MatchRecord>();
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Cfg());
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                var dateStr = csv.GetField("date") ?? "";
                var date    = ParseDate(dateStr);
                var season  = date.Year;
                results.Add(MakeRecord(
                    date:        date,
                    home:        csv.GetField("home") ?? "",
                    away:        csv.GetField("away") ?? "",
                    homeGoals:   ParseInt(csv.GetField("home_goal")),
                    awayGoals:   ParseInt(csv.GetField("away_goal")),
                    competition: csv.GetField("tournament") ?? "BR-Football",
                    season:      season,
                    round:       ""));
            }
            catch { /* skip */ }
        }
        return results;
    }

    // ─── novo_campeonato_brasileiro.csv ───────────────────────────────────────

    public static List<MatchRecord> LoadHistoricalBrasileirao(string path)
    {
        var results = new List<MatchRecord>();
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Cfg());
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                results.Add(MakeRecord(
                    date:        ParseDate(csv.GetField("Data")),
                    home:        csv.GetField("Equipe_mandante") ?? "",
                    away:        csv.GetField("Equipe_visitante") ?? "",
                    homeGoals:   ParseInt(csv.GetField("Gols_mandante")),
                    awayGoals:   ParseInt(csv.GetField("Gols_visitante")),
                    competition: "Brasileirao",
                    season:      ParseInt(csv.GetField("Ano")),
                    round:       csv.GetField("Rodada") ?? "",
                    arena:       csv.GetField("Arena")));
            }
            catch { /* skip */ }
        }
        return results;
    }

    // ─── fifa_data.csv ────────────────────────────────────────────────────────

    public static List<FifaPlayer> LoadFifaPlayers(string path)
    {
        var results = new List<FifaPlayer>();

        // The file may start with a UTF-8 BOM; StreamReader handles that.
        using var reader = new StreamReader(path, detectEncodingFromByteOrderMarks: true);
        using var csv = new CsvReader(reader, Cfg());

        csv.Read(); csv.ReadHeader();

        while (csv.Read())
        {
            try
            {
                var name        = csv.GetField("Name") ?? "";
                var nationality = csv.GetField("Nationality") ?? "";
                var club        = csv.GetField("Club") ?? "";

                int? jersey = null;
                var jerseyRaw = csv.GetField("Jersey Number");
                if (int.TryParse(jerseyRaw, out var j)) jersey = j;

                results.Add(new FifaPlayer
                {
                    SofifaId       = ParseInt(csv.GetField("ID")),
                    Name           = name,
                    Age            = ParseInt(csv.GetField("Age")),
                    Nationality    = nationality,
                    Overall        = ParseInt(csv.GetField("Overall")),
                    Potential      = ParseInt(csv.GetField("Potential")),
                    Club           = club,
                    Position       = csv.GetField("Position") ?? "",
                    JerseyNumber   = jersey,
                    Height         = csv.GetField("Height") ?? "",
                    Weight         = csv.GetField("Weight") ?? "",
                    NameKey        = TeamNameNormalizer.NormalizeForSearch(name),
                    NationalityKey = TeamNameNormalizer.NormalizeForSearch(nationality),
                    ClubKey        = TeamNameNormalizer.NormalizeForSearch(club),
                });
            }
            catch { /* skip */ }
        }
        return results;
    }
}
