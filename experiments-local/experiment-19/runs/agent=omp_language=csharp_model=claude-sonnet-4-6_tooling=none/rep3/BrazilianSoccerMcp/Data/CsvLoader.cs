using System.Globalization;
using System.Text;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads and normalises the six Kaggle CSV files into unified domain models.
/// Each loader is tolerant of missing fields and bad data — rows that fail to
/// parse are silently skipped so a handful of dirty rows don't break startup.
/// </summary>
public static class CsvLoader
{
    // -----------------------------------------------------------------------
    // Common CSV configuration
    // -----------------------------------------------------------------------

    private static CsvConfiguration Cfg(bool hasBom = false) => new(CultureInfo.InvariantCulture)
    {
        MissingFieldFound = null,
        HeaderValidated = null,
        BadDataFound = null,
        // Strip BOM character that may leak into the first header field name
        PrepareHeaderForMatch = args =>
            args.Header.TrimStart('\uFEFF').Trim().ToLowerInvariant(),
    };

    // -----------------------------------------------------------------------
    // Public loaders
    // -----------------------------------------------------------------------

    /// <summary>Brasileirao_Matches.csv — columns: datetime, home_team, away_team, home_goal, away_goal, season, round</summary>
    public static List<Match> LoadBrasileirao(string filePath)
    {
        var results = new List<Match>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, Cfg());

        foreach (var row in csv.GetRecords<dynamic>())
        {
            try
            {
                var dict = (IDictionary<string, object>)row;
                if (!TryGetDate(dict, "datetime", out var date)) continue;
                if (!TryGetInt(dict, "home_goal", out var hg)) continue;
                if (!TryGetInt(dict, "away_goal", out var ag)) continue;

                results.Add(new Match(
                    Competition: "Brasileirão",
                    Date: date,
                    HomeTeam: GetStr(dict, "home_team"),
                    AwayTeam: GetStr(dict, "away_team"),
                    HomeGoals: hg,
                    AwayGoals: ag,
                    Season: TryGetInt(dict, "season", out var season) ? season : null,
                    Round: GetStr(dict, "round"),
                    Stage: null
                ));
            }
            catch { /* skip bad rows */ }
        }
        return results;
    }

    /// <summary>Brazilian_Cup_Matches.csv — columns: round, datetime, home_team, away_team, home_goal, away_goal, season</summary>
    public static List<Match> LoadCopa(string filePath)
    {
        var results = new List<Match>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, Cfg());

        foreach (var row in csv.GetRecords<dynamic>())
        {
            try
            {
                var dict = (IDictionary<string, object>)row;
                if (!TryGetDate(dict, "datetime", out var date)) continue;
                if (!TryGetInt(dict, "home_goal", out var hg)) continue;
                if (!TryGetInt(dict, "away_goal", out var ag)) continue;

                results.Add(new Match(
                    Competition: "Copa do Brasil",
                    Date: date,
                    HomeTeam: GetStr(dict, "home_team"),
                    AwayTeam: GetStr(dict, "away_team"),
                    HomeGoals: hg,
                    AwayGoals: ag,
                    Season: TryGetInt(dict, "season", out var season) ? season : null,
                    Round: GetStr(dict, "round"),
                    Stage: null
                ));
            }
            catch { /* skip bad rows */ }
        }
        return results;
    }

    /// <summary>Libertadores_Matches.csv — columns: datetime, home_team, away_team, home_goal, away_goal, season, stage</summary>
    public static List<Match> LoadLibertadores(string filePath)
    {
        var results = new List<Match>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, Cfg());

        foreach (var row in csv.GetRecords<dynamic>())
        {
            try
            {
                var dict = (IDictionary<string, object>)row;
                if (!TryGetDate(dict, "datetime", out var date)) continue;
                if (!TryGetInt(dict, "home_goal", out var hg)) continue;
                if (!TryGetInt(dict, "away_goal", out var ag)) continue;

                results.Add(new Match(
                    Competition: "Copa Libertadores",
                    Date: date,
                    HomeTeam: GetStr(dict, "home_team"),
                    AwayTeam: GetStr(dict, "away_team"),
                    HomeGoals: hg,
                    AwayGoals: ag,
                    Season: TryGetInt(dict, "season", out var season) ? season : null,
                    Round: null,
                    Stage: GetStr(dict, "stage")
                ));
            }
            catch { /* skip bad rows */ }
        }
        return results;
    }

    /// <summary>BR-Football-Dataset.csv — columns: tournament, home, away, home_goal, away_goal, date</summary>
    public static List<Match> LoadBrFootball(string filePath)
    {
        var results = new List<Match>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, Cfg());

        foreach (var row in csv.GetRecords<dynamic>())
        {
            try
            {
                var dict = (IDictionary<string, object>)row;
                // date column here is "date" not "datetime"
                if (!TryGetDate(dict, "date", out var date)) continue;
                if (!TryGetInt(dict, "home_goal", out var hg)) continue;
                if (!TryGetInt(dict, "away_goal", out var ag)) continue;

                var tournament = GetStr(dict, "tournament");
                if (string.IsNullOrWhiteSpace(tournament)) tournament = "Brazilian Football";

                results.Add(new Match(
                    Competition: tournament,
                    Date: date,
                    HomeTeam: GetStr(dict, "home"),
                    AwayTeam: GetStr(dict, "away"),
                    HomeGoals: hg,
                    AwayGoals: ag,
                    Season: date.Year,
                    Round: null,
                    Stage: null
                ));
            }
            catch { /* skip bad rows */ }
        }
        return results;
    }

    /// <summary>novo_campeonato_brasileiro.csv — Portuguese column names, date in DD/MM/YYYY format</summary>
    public static List<Match> LoadHistorical(string filePath)
    {
        var results = new List<Match>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, Cfg());

        foreach (var row in csv.GetRecords<dynamic>())
        {
            try
            {
                var dict = (IDictionary<string, object>)row;
                // Date format: DD/MM/YYYY
                var dataStr = GetStr(dict, "data");
                if (!TryParseBrazilianDate(dataStr, out var date)) continue;
                if (!TryGetInt(dict, "gols_mandante", out var hg)) continue;
                if (!TryGetInt(dict, "gols_visitante", out var ag)) continue;

                TryGetInt(dict, "ano", out var ano);

                results.Add(new Match(
                    Competition: "Brasileirão Histórico",
                    Date: date,
                    HomeTeam: GetStr(dict, "equipe_mandante"),
                    AwayTeam: GetStr(dict, "equipe_visitante"),
                    HomeGoals: hg,
                    AwayGoals: ag,
                    Season: ano > 0 ? ano : (int?)null,
                    Round: GetStr(dict, "rodada"),
                    Stage: null
                ));
            }
            catch { /* skip bad rows */ }
        }
        return results;
    }

    /// <summary>fifa_data.csv — UTF-8 BOM, first column is unnamed row index</summary>
    public static List<Player> LoadFifa(string filePath)
    {
        var results = new List<Player>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, Cfg());

        foreach (var row in csv.GetRecords<dynamic>())
        {
            try
            {
                var dict = (IDictionary<string, object>)row;

                var name = GetStr(dict, "name");
                if (string.IsNullOrWhiteSpace(name)) continue;

                TryGetInt(dict, "age", out var age);
                TryGetInt(dict, "overall", out var overall);
                TryGetInt(dict, "potential", out var potential);

                results.Add(new Player(
                    FifaId: GetStr(dict, "id"),
                    Name: name,
                    Age: age,
                    Nationality: GetStr(dict, "nationality"),
                    Overall: overall,
                    Potential: potential,
                    Club: GetStr(dict, "club"),
                    Position: GetStr(dict, "position"),
                    JerseyNumber: GetStr(dict, "jersey number"),
                    Height: GetStr(dict, "height"),
                    Weight: GetStr(dict, "weight")
                ));
            }
            catch { /* skip bad rows */ }
        }
        return results;
    }

    // -----------------------------------------------------------------------
    // Helper methods
    // -----------------------------------------------------------------------

    private static string GetStr(IDictionary<string, object> dict, string key)
    {
        foreach (var kv in dict)
        {
            if (string.Equals(kv.Key.Trim(), key, StringComparison.OrdinalIgnoreCase))
                return kv.Value?.ToString()?.Trim() ?? string.Empty;
        }
        return string.Empty;
    }

    private static bool TryGetInt(IDictionary<string, object> dict, string key, out int value)
    {
        value = 0;
        var s = GetStr(dict, key);
        if (string.IsNullOrWhiteSpace(s)) return false;
        // Handle float strings like "1.0"
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
        {
            value = (int)d;
            return true;
        }
        return false;
    }

    private static readonly string[] DateFormats =
    [
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "MM/dd/yyyy",
    ];

    private static bool TryGetDate(IDictionary<string, object> dict, string key, out DateTime value)
    {
        value = default;
        var s = GetStr(dict, key);
        return TryParseDate(s, out value);
    }

    private static bool TryParseDate(string s, out DateTime value)
    {
        value = default;
        if (string.IsNullOrWhiteSpace(s)) return false;
        return DateTime.TryParseExact(s, DateFormats, CultureInfo.InvariantCulture,
                   DateTimeStyles.None, out value)
               || DateTime.TryParse(s, out value);
    }

    private static bool TryParseBrazilianDate(string s, out DateTime value)
    {
        value = default;
        if (string.IsNullOrWhiteSpace(s)) return false;
        return DateTime.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture,
            DateTimeStyles.None, out value);
    }
}
