namespace BrazilianSoccerMcp.Models;

public class PlayerRecord
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public int Age { get; set; }
    public string Nationality { get; set; } = "";
    public int Overall { get; set; }
    public int Potential { get; set; }
    public string Club { get; set; } = "";
    public string Position { get; set; } = "";
    public string? JerseyNumber { get; set; }
    public string? Height { get; set; }
    public string? Weight { get; set; }
    public int? Crossing { get; set; }
    public int? Finishing { get; set; }
    public int? Dribbling { get; set; }
    public int? HeadingAccuracy { get; set; }
    public int? ShortPassing { get; set; }
    public int? Stamina { get; set; }
    public string? Value { get; set; }
    public string? Wage { get; set; }
}
