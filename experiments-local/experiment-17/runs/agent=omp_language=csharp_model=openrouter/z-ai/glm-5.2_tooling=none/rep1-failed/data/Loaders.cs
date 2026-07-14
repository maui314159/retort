// ============================================================================
// File: Data/Loaders.cs
// ----------------------------------------------------------------------------
// Context: Reads the six CSV files into the unified in-memory model.
//
// All loaders share the same CsvHelper configuration (InvariantCulture,
// lenient header/missing-field handling). Robust parsing:
//   - Goals arrive as int, quoted-string int ("2"), or float ("1.0");
//     ParseInt handles all three.
//   - Dates appear as ISO "2012-05-19 18:30:00", ISO date "2023-09-24",
//     or Brazilian "29/03/2003"; ParseDate tries each.
//   - The FIFA file has a BOM and an unnamed leading column; CsvHelper skips
//     it because no Player property maps to an empty header.
//
// Each loader tags records with its source filename and a consistent
// competition label (Competitions constants) so cross-file queries and
// provenance reporting work uniformly.
// ============================================================================

using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

internal static class Loaders
{
    private static readonly CsvConfiguration Config = new(CultureInfo.InvariantCulture)
    {
        HeaderValidated = null,
        MissingFieldFound = null,
        BadDataFound = null,
        PrepareHeaderForMatch = args => args.Header.Trim(),
    };

    public static List<SoccerMatch> LoadBrasileirao(string path) =>
        ReadMatches(path, row => BuildMatch(
            competition: Competitions.Brasileirao,
            source: "Brasileirao_Matches.csv",
            dateRaw: row.GetField("datetime"),
            homeRaw: row.GetField("home_team"),
            awayRaw: row.GetField("away_team"),
            homeGoalRaw: row.GetField("home_goal"),
            awayGoalRaw: row.GetField("away_goal"),
            seasonRaw: row.GetField("season"),
            roundRaw: row.GetField("round")));

    public static List<SoccerMatch> LoadCopaDoBrasil(string path) =>
        ReadMatches(path, row => BuildMatch(
            competition: Competitions.CopaDoBrasil,
            source: "Brazilian_Cup_Matches.csv",
            dateRaw: row.GetField("datetime"),
            homeRaw: row.GetField("home_team"),
            awayRaw: row.GetField("away_team"),
            homeGoalRaw: row.GetField("home_goal"),
            awayGoalRaw: row.GetField("away_goal"),
            seasonRaw: row.GetField("season"),
            roundRaw: row.GetField("round")));

    public static List<SoccerMatch> LoadLibertadores(string path) =>
        ReadMatches(path, row => BuildMatch(
            competition: Competitions.Libertadores,
            source: "Libertadores_Matches.csv",
            dateRaw: row.GetField("datetime"),
            homeRaw: row.GetField("home_team"),
            awayRaw: row.GetField("away_team"),
            homeGoalRaw: row.GetField("home_goal"),
            awayGoalRaw: row.GetField("away_goal"),
            seasonRaw: row.GetField("season"),
            stageRaw: row.GetField("stage")));

    public static List<SoccerMatch> LoadHistoricalBrasileirao(string path) =>
        ReadMatches(path, row => BuildMatch(
            competition: Competitions.BrasileiraoHistorical,
            source: "novo_campeonato_brasileiro.csv",
            dateRaw: row.GetField("Data"),
            homeRaw: row.GetField("Equipe_mandante"),
            awayRaw: row.GetField("Equipe_visitante"),
            homeGoalRaw: row.GetField("Gols_mandante"),
            awayGoalRaw: row.GetField("Gols_visitante"),
            seasonRaw: row.GetField("Ano"),
            roundRaw: row.GetField("Rodada"),
            stadiumRaw: row.GetField("Arena")));

    public static List<SoccerMatch> LoadBrFootball(string path)
    {
        var matches = new List<SoccerMatch>();
        ForEachRow(path, row =>
        {
            var tournament = (row.GetField("tournament") ?? "").Trim();
            var dateField = row.GetField("date");
            // BR-Football has no season column; derive it from the date year
            // so its matches are season-queryable alongside the other files.
            var seasonRaw = dateField is { } d && d.Length >= 4 && int.TryParse(d.AsSpan(0, 4), out var yr) ? yr.ToString() : null;
            if (BuildMatch(
                competition: MapTournament(tournament),
                source: "BR-Football-Dataset.csv",
                dateRaw: CombineDateAndTime(dateField, row.GetField("time")),
                homeRaw: row.GetField("home"),
                awayRaw: row.GetField("away"),
                homeGoalRaw: row.GetField("home_goal"),
                awayGoalRaw: row.GetField("away_goal"),
                seasonRaw: seasonRaw,
                stageRaw: tournament) is { } m) // preserve tournament label as stage
            {
                matches.Add(m);
            }
        });
        return matches;
    }

    public static List<SoccerPlayer> LoadPlayers(string path)
    {
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Config);
        return csv.GetRecords<SoccerPlayer>().ToList();
    }

    // ---- helpers -----------------------------------------------------------

    private static string MapTournament(string tournament) => tournament switch
    {
        "Serie A" => Competitions.Brasileirao,
        "Serie B" => "Série B",
        "Copa do Brasil" => Competitions.CopaDoBrasil,
        "Libertadores" => Competitions.Libertadores,
        "Sul-Americana" => "Copa Sul-Americana",
        _ => tournament
    };
    private static void ForEachRow(string path, Action<CsvReader> action)
    {
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            action(csv);
        }
    }

    private static List<SoccerMatch> ReadMatches(string path, Func<CsvReader, SoccerMatch?> project)
    {
        var matches = new List<SoccerMatch>();
        ForEachRow(path, row =>
        {
            try
            {
                if (project(row) is { } m)
                    matches.Add(m);
            }
            catch (CsvHelper.MissingFieldException)
            {
                // Skip rows that don't conform to the expected schema.
            }
        });
        return matches;
    }

    private static SoccerMatch? BuildMatch(
        string competition, string source,
        string? dateRaw, string? homeRaw, string? awayRaw,
        string? homeGoalRaw, string? awayGoalRaw,
        string? seasonRaw = null, string? roundRaw = null,
        string? stageRaw = null, string? stadiumRaw = null)
    {
        if (string.IsNullOrWhiteSpace(homeRaw) || string.IsNullOrWhiteSpace(awayRaw))
            return null;

        var homeKey = TeamNameNormalizer.Parse(homeRaw);
        var awayKey = TeamNameNormalizer.Parse(awayRaw);

        return new SoccerMatch
        {
            Competition = competition,
            Source = source,
            Date = ParseDate(dateRaw),
            HomeTeamRaw = homeRaw!.Trim(),
            AwayTeamRaw = awayRaw!.Trim(),
            HomeKey = homeKey,
            AwayKey = awayKey,
            HomeGoals = ParseInt(homeGoalRaw),
            AwayGoals = ParseInt(awayGoalRaw),
            Season = ParseInt(seasonRaw),
            Round = string.IsNullOrWhiteSpace(roundRaw) ? null : roundRaw!.Trim(),
            Stage = string.IsNullOrWhiteSpace(stageRaw) ? null : stageRaw!.Trim(),
            Stadium = string.IsNullOrWhiteSpace(stadiumRaw) ? null : stadiumRaw!.Trim(),
        };
    }

    private static DateTime? ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim();

        if (DateTime.TryParseExact(s, "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var iso))
            return iso;

        if (DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var isoDate))
            return isoDate;

        if (DateTime.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var br))
            return br;

        if (DateTime.TryParse(s, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var loose))
            return loose;

        return null;
    }

    private static string? CombineDateAndTime(string? dateRaw, string? timeRaw)
    {
        if (string.IsNullOrWhiteSpace(dateRaw)) return dateRaw;
        if (string.IsNullOrWhiteSpace(timeRaw)) return dateRaw;
        return $"{dateRaw} {timeRaw}";
    }

    /// <summary>
    /// Parse a goal/season value that may be an int, a quoted string int,
    /// or a float like "1.0". Returns null when blank or unparseable.
    /// </summary>
    private static int? ParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw!.Trim().Trim('"');
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (int)Math.Round(d);
        return null;
    }
}
