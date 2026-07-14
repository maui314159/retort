// =============================================================================
// Brazilian Soccer MCP Server
// File: BrazilianCupCsvLoader.cs
// Purpose: Stream-reads Brazilian_Cup_Matches.csv into MatchRecord rows.
// Context: This dataset has no state code; team names appear with a
//          " - ST" suffix on a few hundred rows but not all, so the
//          normalizer is the only safe way to compare them.
// =============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

public static class BrazilianCupCsvLoader
{
    public const string DefaultFileName = "data/kaggle/Brazilian_Cup_Matches.csv";

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
            var rawHome = csv.GetField("home_team") ?? string.Empty;
            var rawAway = csv.GetField("away_team") ?? string.Empty;
            var rawDt = csv.GetField("datetime");
            var date = DateTimeParser.TryParse(rawDt, out var d) ? d : default;

            results.Add(new MatchRecord
            {
                Competition = Competition.CopaDoBrasil,
                HomeTeam = rawHome,
                AwayTeam = rawAway,
                HomeGoal = ParseIntSafe(csv.GetField("home_goal")),
                AwayGoal = ParseIntSafe(csv.GetField("away_goal")),
                Season = ParseIntSafe(csv.GetField("season")),
                Date = date,
                Round = NullIfEmpty(csv.GetField("round")),
            });
        }
        return results;
    }

    private static int ParseIntSafe(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : 0;

    private static string? NullIfEmpty(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim().Trim('"');
}
