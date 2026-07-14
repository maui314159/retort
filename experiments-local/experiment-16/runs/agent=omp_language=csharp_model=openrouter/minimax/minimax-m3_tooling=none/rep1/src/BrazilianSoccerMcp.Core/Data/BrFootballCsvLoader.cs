// =============================================================================
// Brazilian Soccer MCP Server
// File: BrFootballCsvLoader.cs
// Purpose: Stream-reads BR-Football-Dataset.csv (10k+ matches) into
//          MatchRecord rows with extended statistics populated.
// Context: This dataset covers multiple competitions ("Brasileirão", "Copa
//          do Brasil", "Libertadores" etc.) and provides half-time
//          results, corners, attacks, and shots -- fields the other
//          datasets do not have. We map the 'tournament' column to a
//          coarse Competition value and stash extended stats in the
//          dedicated nullable fields.
// =============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

public static class BrFootballCsvLoader
{
    public const string DefaultFileName = "data/kaggle/BR-Football-Dataset.csv";

    public static IReadOnlyList<MatchRecord> Load(string path)
    {
        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
            TrimOptions = TrimOptions.Trim,
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, cfg);
        csv.Read();
        csv.ReadHeader();

        var results = new List<MatchRecord>();
        while (csv.Read())
        {
            var rawHome = csv.GetField("home") ?? string.Empty;
            var rawAway = csv.GetField("away") ?? string.Empty;
            var rawDate = csv.GetField("date");
            var date = DateTimeParser.TryParse(rawDate, out var d) ? d : default;
            var tournament = NullIfEmpty(csv.GetField("tournament")) ?? "Brasileirão";

            // Derive season from the year of the match. The CSV itself has
            // no explicit season column.
            var season = date.Year;

            results.Add(new MatchRecord
            {
                Competition = Competition.BrazilianExtended,
                HomeTeam = rawHome,
                AwayTeam = rawAway,
                HomeGoal = ParseIntSafe(csv.GetField("home_goal")),
                AwayGoal = ParseIntSafe(csv.GetField("away_goal")),
                Season = season,
                Date = date,
                Round = tournament,                       // store tournament in Round for filtering
                HomeCorners = ParseIntSafeNullable(csv.GetField("home_corner")),
                AwayCorners = ParseIntSafeNullable(csv.GetField("away_corner")),
                HomeShots = ParseIntSafeNullable(csv.GetField("home_shots")),
                AwayShots = ParseIntSafeNullable(csv.GetField("away_shots")),
                HomeAttacks = ParseIntSafeNullable(csv.GetField("home_attack")),
                AwayAttacks = ParseIntSafeNullable(csv.GetField("away_attack")),
                HalfTimeHomeResult = NullIfEmpty(csv.GetField("ht_result")),
                HalfTimeAwayResult = NullIfEmpty(csv.GetField("at_result")),
            });
        }
        return results;
    }

    private static int ParseIntSafe(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : 0;

    private static int? ParseIntSafeNullable(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : null;

    private static string? NullIfEmpty(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim().Trim('"');
}
