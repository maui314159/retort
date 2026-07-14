// BrazilianSoccerMcp.Core - FIFA player model.
// Only the columns most useful for the MCP query tools are captured; the
// raw row is retained so callers needing a rarely used attribute can still
// access it through <see cref="ExtraColumns"/>.
using System.Globalization;

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// A single FIFA player record from <c>fifa_data.csv</c>.
/// Numeric skill ratings are stored in <see cref="Attributes"/> keyed by the
/// CSV header (e.g. "Crossing", "Finishing", "Dribbling").
/// </summary>
public sealed class Player
{
    public int Id { get; init; }
    public string Name { get; init; } = "";
    public int Age { get; init; }
    public string Nationality { get; init; } = "";
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = "";
    public string Position { get; init; } = "";
    public int JerseyNumber { get; init; }
    public string PreferredFoot { get; init; } = "";
    public string Height { get; init; } = "";
    public string Weight { get; init; } = "";
    public string Value { get; init; } = "";
    public string Wage { get; init; } = "";

    /// <summary>Numeric skill ratings keyed by CSV column header.</summary>
    public IReadOnlyDictionary<string, int> Attributes { get; init; }
        = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

    public int Attribute(string name) =>
        Attributes.TryGetValue(name, out var v) ? v : 0;

    public bool IsBrazilian =>
        Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase);
}
