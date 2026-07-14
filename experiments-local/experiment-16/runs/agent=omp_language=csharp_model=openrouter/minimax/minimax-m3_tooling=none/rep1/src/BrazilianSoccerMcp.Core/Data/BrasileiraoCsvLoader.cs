// =============================================================================
// Brazilian Soccer MCP Server
// File: BrasileiraoCsvLoader.cs
// Purpose: Stream-reads Brasileirao_Matches.csv into MatchRecord rows.
// Context: The Brasileirão file uses 2-letter state suffixes on every team
//          name (e.g. "Flamengo-RJ"). We preserve the raw string on the
//          record and let TeamNameNormalizer handle comparisons at query
//          time -- this keeps the data layer free of normalization state.
// =============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

public static class BrasileiraoCsvLoader
{
    /// <summary>Path of the source CSV relative to the project working dir.</summary>
    public const string DefaultFileName = "data/kaggle/Brasileirao_Matches.csv";

    public static IReadOnlyList<MatchRecord> Load(string path)
    {
        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,            // tolerate heterogeneous rows
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
                Competition = Competition.Brasileirao,
                HomeTeam = rawHome,
                AwayTeam = rawAway,
                HomeTeamState = NullIfEmpty(csv.GetField("home_team_state")),
                AwayTeamState = NullIfEmpty(csv.GetField("away_team_state")),
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
