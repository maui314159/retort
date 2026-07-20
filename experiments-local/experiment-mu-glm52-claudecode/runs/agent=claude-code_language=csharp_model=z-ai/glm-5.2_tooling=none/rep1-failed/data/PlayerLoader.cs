// =============================================================================
// File: Data/PlayerLoader.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Loads fifa_data.csv (FIFA 19 squad snapshot, ~18.2k players) into a list
//   of PlayerRecord. Only the columns surfaced by the MCP query API are
//   retained; the 80+ positional skill ratings are skipped to keep memory
//   lean.
//
// fifa_data.csv quirks handled here:
//   - The file ships with a UTF-8 BOM and an unnamed leading index column.
//     CsvReader strips the BOM; we read positional columns starting at index 1
//     (the real ID) rather than trusting the empty header name.
//   - "Overall" / "Potential" / "Age" / "Jersey Number" are integers but may be
//     blank; missing values become null rather than crashing the query layer.
//   - "Position" can be blank (goalkeepers sometimes carry it; substitutes too).
//
// Header reference (positional, after the leading unnamed index column):
//   [0]=unnamed  [1]=ID  [2]=Name  [3]=Age  [4]=Photo  [5]=Nationality
//   [6]=Flag  [7]=Overall  [8]=Potential  [9]=Club  [10]=Club Logo  [11]=Value
//   [12]=Wage  ... [21]=Position  [22]=Jersey Number  [13]=Preferred Foot
// =============================================================================
namespace BrazilianSoccerMcp.Data;

using System;
using System.Collections.Generic;
using System.Globalization;
using BrazilianSoccerMcp.Csv;
using BrazilianSoccerMcp.Models;

public static class PlayerLoader
{
    // Positional offsets (1-based because the leading unnamed column occupies [0]).
    private const int ColId = 1;
    private const int ColName = 2;
    private const int ColAge = 3;
    private const int ColNationality = 5;
    private const int ColOverall = 7;
    private const int ColPotential = 8;
    private const int ColClub = 9;
    private const int ColValue = 11;
    private const int ColWage = 12;
    private const int ColPreferredFoot = 14;
    private const int ColPosition = 21;
    private const int ColJersey = 22;

    public static List<PlayerRecord> Load(string path)
    {
        var players = new List<PlayerRecord>(18_500);
        if (!System.IO.File.Exists(path)) return players;
        var rows = CsvReader.ReadAll(path);

        for (int i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length <= ColPosition) continue;

            var p = new PlayerRecord
            {
                Id = TryParseInt(r[ColId]) ?? 0,
                Name = r[ColName].Trim(),
                Age = TryParseInt(r[ColAge]),
                Nationality = r[ColNationality].Trim(),
                Overall = TryParseInt(r[ColOverall]),
                Potential = TryParseInt(r[ColPotential]),
                Club = r[ColClub].Trim(),
                Value = NullIfBlank(r[ColValue]),
                Wage = NullIfBlank(r[ColWage]),
                PreferredFoot = NullIfBlank(r[ColPreferredFoot]),
                Position = NullIfBlank(r[ColPosition]),
                JerseyNumber = TryParseInt(r[ColJersey]),
            };
            if (string.IsNullOrWhiteSpace(p.Name)) continue;
            p.ClubNormalized = TeamNameNormalizer.Normalize(p.Club);
            players.Add(p);
        }
        return players;
    }

    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        if (int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var v))
            return v;
        if (double.TryParse(raw.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    private static string? NullIfBlank(string? s)
        => string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
