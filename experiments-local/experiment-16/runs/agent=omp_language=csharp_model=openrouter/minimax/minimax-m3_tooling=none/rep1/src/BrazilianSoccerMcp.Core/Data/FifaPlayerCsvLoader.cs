// =============================================================================
// Brazilian Soccer MCP Server
// File: FifaPlayerCsvLoader.cs
// Purpose: Stream-reads fifa_data.csv into PlayerRecord rows.
// Context: The FIFA file ships with a UTF-8 BOM (those "﻿" bytes at the
//          start of the header) and uses a leading unnamed column
//          (the row index) -- CsvHelper handles both with the defaults
//          below. We project only the documented fields so PlayerRecord
//          stays small.
// =============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

public static class FifaPlayerCsvLoader
{
    public const string DefaultFileName = "data/kaggle/fifa_data.csv";

    public static IReadOnlyList<PlayerRecord> Load(string path)
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

        var results = new List<PlayerRecord>(capacity: 20_000);
        while (csv.Read())
        {
            results.Add(new PlayerRecord
            {
                Id = ParseIntSafe(csv.GetField("ID")),
                Name = NullIfEmpty(csv.GetField("Name")) ?? string.Empty,
                Age = ParseIntNullable(csv.GetField("Age")),
                Photo = NullIfEmpty(csv.GetField("Photo")),
                Nationality = NullIfEmpty(csv.GetField("Nationality")),
                Overall = ParseIntNullable(csv.GetField("Overall")),
                Potential = ParseIntNullable(csv.GetField("Potential")),
                Club = NullIfEmpty(csv.GetField("Club")),
                JerseyNumber = ParseIntNullable(csv.GetField("Jersey Number")),
                Value = NullIfEmpty(csv.GetField("Value")),
                Wage = NullIfEmpty(csv.GetField("Wage")),
                PreferredFoot = NullIfEmpty(csv.GetField("Preferred Foot")),
                InternationalReputation = NullIfEmpty(csv.GetField("International Reputation")),
                WeakFoot = NullIfEmpty(csv.GetField("Weak Foot")),
                SkillMoves = NullIfEmpty(csv.GetField("Skill Moves")),
                WorkRate = NullIfEmpty(csv.GetField("Work Rate")),
                BodyType = NullIfEmpty(csv.GetField("Body Type")),
                RealFace = NullIfEmpty(csv.GetField("Real Face")),
                Position = NullIfEmpty(csv.GetField("Position")),
                Joined = NullIfEmpty(csv.GetField("Joined")),
                LoanedFrom = NullIfEmpty(csv.GetField("Loaned From")),
                ContractValidUntil = NullIfEmpty(csv.GetField("Contract Valid Until")),
                Height = NullIfEmpty(csv.GetField("Height")),
                Weight = NullIfEmpty(csv.GetField("Weight")),
                Crossing = ParseIntNullable(csv.GetField("Crossing")),
                Finishing = ParseIntNullable(csv.GetField("Finishing")),
                HeadingAccuracy = ParseIntNullable(csv.GetField("HeadingAccuracy")),
                ShortPassing = ParseIntNullable(csv.GetField("ShortPassing")),
                Volleys = ParseIntNullable(csv.GetField("Volleys")),
                Dribbling = ParseIntNullable(csv.GetField("Dribbling")),
                Curve = ParseIntNullable(csv.GetField("Curve")),
                FKAccuracy = ParseIntNullable(csv.GetField("FKAccuracy")),
                LongPassing = ParseIntNullable(csv.GetField("LongPassing")),
                BallControl = ParseIntNullable(csv.GetField("BallControl")),
                Acceleration = ParseIntNullable(csv.GetField("Acceleration")),
                SprintSpeed = ParseIntNullable(csv.GetField("SprintSpeed")),
                Agility = ParseIntNullable(csv.GetField("Agility")),
                Reactions = ParseIntNullable(csv.GetField("Reactions")),
                Balance = ParseIntNullable(csv.GetField("Balance")),
                ShotPower = ParseIntNullable(csv.GetField("ShotPower")),
                Jumping = ParseIntNullable(csv.GetField("Jumping")),
                Stamina = ParseIntNullable(csv.GetField("Stamina")),
                Strength = ParseIntNullable(csv.GetField("Strength")),
                LongShots = ParseIntNullable(csv.GetField("LongShots")),
                Aggression = ParseIntNullable(csv.GetField("Aggression")),
                Interceptions = ParseIntNullable(csv.GetField("Interceptions")),
                Positioning = ParseIntNullable(csv.GetField("Positioning")),
                Vision = ParseIntNullable(csv.GetField("Vision")),
                Penalties = ParseIntNullable(csv.GetField("Penalties")),
                Composure = ParseIntNullable(csv.GetField("Composure")),
                Marking = ParseIntNullable(csv.GetField("Marking")),
                StandingTackle = ParseIntNullable(csv.GetField("StandingTackle")),
                SlidingTackle = ParseIntNullable(csv.GetField("SlidingTackle")),
                GKDiving = ParseIntNullable(csv.GetField("GKDiving")),
                GKHandling = ParseIntNullable(csv.GetField("GKHandling")),
                GKKicking = ParseIntNullable(csv.GetField("GKKicking")),
                GKPositioning = ParseIntNullable(csv.GetField("GKPositioning")),
                GKReflexes = ParseIntNullable(csv.GetField("GKReflexes")),
                ReleaseClause = NullIfEmpty(csv.GetField("Release Clause")),
            });
        }
        return results;
    }

    private static int ParseIntSafe(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : 0;

    private static int? ParseIntNullable(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : null;

    private static string? NullIfEmpty(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim().Trim('"');
}
