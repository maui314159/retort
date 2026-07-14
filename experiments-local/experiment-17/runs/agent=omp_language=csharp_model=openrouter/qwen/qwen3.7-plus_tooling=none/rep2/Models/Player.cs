namespace BrazilianSoccerMcp.Models;

public class Player
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public int Age { get; set; }
    public string Nationality { get; set; } = string.Empty;
    public int Overall { get; set; }
    public int Potential { get; set; }
    public string Club { get; set; } = string.Empty;
    public string Position { get; set; } = string.Empty;
    public string? Height { get; set; }
    public string? Weight { get; set; }
}
