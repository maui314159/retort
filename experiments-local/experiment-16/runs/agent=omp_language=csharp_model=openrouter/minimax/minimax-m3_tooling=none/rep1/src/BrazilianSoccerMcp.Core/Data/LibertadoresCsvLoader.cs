// =============================================================================
// Brazilian Soccer MCP Server
// File: LibertadoresCsvLoader.cs
// Purpose: Stream-reads Libertadores_Matches.csv into MatchRecord rows.
// Context: Goals are stored as quoted strings in this file ("2" not 2), so
//          ParseIntSafe is the only safe way to extract them.
// =============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

public static class LibertadoresCsvLoader
{
    public const string DefaultFileName = "data/kaggle/Libertadores_Matches.csv";

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
                Competition = Competition.Libertadores,
                HomeTeam = rawHome,
                AwayTeam = rawAway,
                HomeGoal = ParseIntSafe(csv.GetField("home_goal")),
                AwayGoal = ParseIntSafe(csv.GetField("away_goal")),
                Season = ParseIntSafe(csv.GetField("season")),
                Date = date,
                Stage = NullIfEmpty(csv.GetField("stage")),
            });
        }
        return results;
    }

    private static int ParseIntSafe(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : 0;

    private static string? NullIfEmpty(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim().Trim('"');
}
