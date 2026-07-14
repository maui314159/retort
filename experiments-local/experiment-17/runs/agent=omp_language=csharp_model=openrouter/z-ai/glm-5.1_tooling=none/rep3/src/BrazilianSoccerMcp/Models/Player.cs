namespace BrazilianSoccerMcp.Models;

public sealed record Player
{
    public int Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public int Age { get; init; }
    public string Nationality { get; init; } = string.Empty;
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = string.Empty;
    public string Position { get; init; } = string.Empty;
    public int? JerseyNumber { get; init; }
    public string Height { get; init; } = string.Empty;
    public string Weight { get; init; } = string.Empty;
    public int Crossing { get; init; }
    public int Finishing { get; init; }
    public int HeadingAccuracy { get; init; }
    public int ShortPassing { get; init; }
    public int Dribbling { get; init; }
    public int Curve { get; init; }
    public int LongPassing { get; init; }
    public int BallControl { get; init; }
    public int Acceleration { get; init; }
    public int SprintSpeed { get; init; }
    public int Agility { get; init; }
    public int Reactions { get; init; }
    public int Stamina { get; init; }
    public int Strength { get; init; }
    public int ShotPower { get; init; }
    public int Interceptions { get; init; }
    public int Positioning { get; init; }
    public int Vision { get; init; }
    public int StandingTackle { get; init; }
    public int SlidingTackle { get; init; }

    public string ClubNormalized => Data.TeamNameNormalizer.Normalize(Club);
}
