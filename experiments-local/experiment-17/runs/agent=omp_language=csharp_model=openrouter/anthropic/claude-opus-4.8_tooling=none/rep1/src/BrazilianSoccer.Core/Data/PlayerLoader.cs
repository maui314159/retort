// -----------------------------------------------------------------------------
// File: Data/PlayerLoader.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Loads fifa_data.csv (~18k players, ~90 columns) into the slim Player model.
//   The file's first column is an unnamed, BOM-prefixed row index; we read every
//   field by its header name (ID, Name, Nationality, Overall, ...) so that stray
//   leading column is simply ignored.
//
//   Rows missing a usable ID or Name are skipped — they cannot be referenced or
//   displayed meaningfully. All numeric fields are parsed tolerantly (null on
//   junk) via CsvFields so one malformed cell never aborts the load.
// -----------------------------------------------------------------------------

using System.Globalization;
using BrazilianSoccer.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccer.Core.Data;

/// <summary>Loads the FIFA player database into <see cref="Player"/> records.</summary>
public static class PlayerLoader
{
    private static CsvConfiguration Config => new(CultureInfo.InvariantCulture)
    {
        HasHeaderRecord = true,
        TrimOptions = TrimOptions.Trim,
        MissingFieldFound = null,
        BadDataFound = null,
        HeaderValidated = null,
        DetectColumnCountChanges = false,
    };

    /// <summary>Loads every player from <paramref name="dataDir"/>/fifa_data.csv.</summary>
    public static List<Player> LoadAll(string dataDir)
        => Load(Path.Combine(dataDir, "fifa_data.csv"));

    public static List<Player> Load(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException($"Player data file not found: {path}", path);

        var players = new List<Player>(capacity: 18_500);

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Config);
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var id = CsvFields.ParseInt(csv.GetField("ID"));
            var name = CsvFields.Clean(csv.GetField("Name"));
            if (id is null || name is null)
                continue;

            players.Add(new Player
            {
                Id = id.Value,
                Name = name,
                Age = CsvFields.ParseInt(csv.GetField("Age")),
                Nationality = CsvFields.Clean(csv.GetField("Nationality")) ?? "Unknown",
                Overall = CsvFields.ParseInt(csv.GetField("Overall")),
                Potential = CsvFields.ParseInt(csv.GetField("Potential")),
                Club = CsvFields.Clean(csv.GetField("Club")),
                Position = CsvFields.Clean(csv.GetField("Position")),
                JerseyNumber = CsvFields.ParseInt(csv.GetField("Jersey Number")),
                Height = CsvFields.Clean(csv.GetField("Height")),
                Weight = CsvFields.Clean(csv.GetField("Weight")),
                PreferredFoot = CsvFields.Clean(csv.GetField("Preferred Foot")),
            });
        }

        return players;
    }
}
