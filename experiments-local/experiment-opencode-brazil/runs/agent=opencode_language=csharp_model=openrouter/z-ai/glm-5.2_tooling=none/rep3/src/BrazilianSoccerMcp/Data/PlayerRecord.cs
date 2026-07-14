namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Subset of the FIFA player database that we actually expose through the
/// MCP tools. We intentionally keep a small set of attributes to avoid
/// blowing up tool responses, but the loader is tolerant of missing columns.
/// </summary>
public sealed class PlayerRecord
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public int Age { get; set; }
    public string Nationality { get; set; } = string.Empty;
    public int Overall { get; set; }
    public int Potential { get; set; }
    public string Club { get; set; } = string.Empty;
    public string Position { get; set; } = string.Empty;
    public int JerseyNumber { get; set; }
    public string Height { get; set; } = string.Empty;
    public string Weight { get; set; } = string.Empty;

    public override string ToString()
        => $"{Name} - Overall:{Overall} {Position} {Club} ({Nationality})";
}
