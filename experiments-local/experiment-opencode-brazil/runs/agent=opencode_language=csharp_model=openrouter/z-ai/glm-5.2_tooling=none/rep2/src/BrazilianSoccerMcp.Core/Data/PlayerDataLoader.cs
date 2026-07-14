// BrazilianSoccerMcp.Core - FIFA player data loader.
// The fifa_data.csv file has an unnamed leading index column and ~80 columns;
// we capture the core identity/club fields plus every numeric skill column we
// can find, storing them in <see cref="Player.Attributes"/> for later filtering.
using BrazilianSoccerMcp.Core.Data.Csv;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>Loads <c>fifa_data.csv</c> into a normalized <see cref="Player"/> list.</summary>
public sealed class PlayerDataLoader
{
    public const string FifaFile = "fifa_data.csv";

    // Numeric skill columns captured into Player.Attributes.
    private static readonly HashSet<string> SkillColumns = new(StringComparer.OrdinalIgnoreCase)
    {
        "Crossing","Finishing","HeadingAccuracy","ShortPassing","Volleys",
        "Dribbling","Curve","FKAccuracy","LongPassing","BallControl",
        "Acceleration","SprintSpeed","Agility","Reactions","Balance",
        "ShotPower","Jumping","Stamina","Strength","LongShots","Aggression",
        "Interceptions","Positioning","Vision","Penalties","Composure",
        "Marking","StandingTackle","SlidingTackle",
        "GKDiving","GKHandling","GKKicking","GKPositioning","GKReflexes",
        "Overall","Potential"
    };

    public IReadOnlyList<Player> Load(string directory)
    {
        var path = Path.Combine(directory, FifaFile);
        if (!File.Exists(path)) return Array.Empty<Player>();
        var rows = SimpleCsvReader.Read(path);
        var players = new List<Player>(rows.Count);
        foreach (var row in rows)
        {
            try { players.Add(MapPlayer(row)); }
            catch { /* skip malformed row */ }
        }
        return players;
    }

    private static Player MapPlayer(CsvRow row)
    {
        var attrs = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var header in row.Headers)
        {
            if (SkillColumns.Contains(header))
            {
                var raw = row.Get(header).Trim().Trim('"');
                // Some skill columns are stored like "88+2"; take the base.
                var plusIdx = raw.IndexOf('+');
                if (plusIdx >= 0) raw = raw.Substring(0, plusIdx);
                if (int.TryParse(raw, out var v)) attrs[header] = v;
            }
        }

        return new Player
        {
            Id = row.GetInt("ID"),
            Name = row.Get("Name"),
            Age = row.GetInt("Age"),
            Nationality = row.Get("Nationality"),
            Overall = row.GetInt("Overall"),
            Potential = row.GetInt("Potential"),
            Club = row.Get("Club"),
            Position = row.Get("Position"),
            JerseyNumber = row.GetInt("Jersey Number"),
            PreferredFoot = row.Get("Preferred Foot"),
            Height = row.Get("Height"),
            Weight = row.Get("Weight"),
            Value = row.Get("Value"),
            Wage = row.Get("Wage"),
            Attributes = attrs
        };
    }
}
