// Brazilian Soccer MCP Server - Player model
//
// Context: Subset of the FIFA player database (fifa_data.csv) fields that are
// useful for natural-language queries. Only the columns required to answer the
// spec's player questions are retained; the ~75 raw attribute columns are not
// needed and are intentionally dropped to keep memory and payload sizes small.

namespace BrazilianSoccerMcp.Models;

/// <summary>A player record sourced from the FIFA player database.</summary>
public sealed class Player
{
    public long? Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public int? Age { get; set; }
    public string Nationality { get; set; } = string.Empty;
    public int? Overall { get; set; }
    public int? Potential { get; set; }
    public string Club { get; set; } = string.Empty;
    public string? Position { get; set; }
    public int? JerseyNumber { get; set; }
    public string? PreferredFoot { get; set; }
    public string? Height { get; set; }
    public string? Weight { get; set; }
    public string? Value { get; set; }
    public string? Wage { get; set; }

    /// <summary>One-line summary used by the formatted tool output.</summary>
    public string Summary
    {
        get
        {
            var rating = Overall.HasValue ? $"Overall: {Overall}" : "Overall: n/a";
            var pos = string.IsNullOrWhiteSpace(Position) ? "" : $", Position: {Position}";
            var club = string.IsNullOrWhiteSpace(Club) ? "" : $", Club: {Club}";
            return $"{Name} - {rating}{pos}{club}";
        }
    }
}
