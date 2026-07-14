namespace BrazilianSoccerMCP.Models;

/// <summary>
/// FIFA player data model.
/// </summary>
public class Player
{
    public int ID { get; set; }
    public string Name { get; set; } = "";
    public int Age { get; set; }
    public string Nationality { get; set; } = "";
    public int Overall { get; set; }
    public int Potential { get; set; }
    public string Club { get; set; } = "";
    public string Position { get; set; } = "";
    public int? JerseyNumber { get; set; }
    public string PreferredFoot { get; set; } = "";
    public string Height { get; set; } = "";
    public string Weight { get; set; } = "";
    public string WorkRate { get; set; } = "";

    // Skill ratings
    public int Crossing { get; set; }
    public int Finishing { get; set; }
    public int HeadingAccuracy { get; set; }
    public int ShortPassing { get; set; }
    public int Volleys { get; set; }
    public int Dribbling { get; set; }
    public int Curve { get; set; }
    public int FKAccuracy { get; set; }
    public int LongPassing { get; set; }
    public int BallControl { get; set; }
    public int Acceleration { get; set; }
    public int SprintSpeed { get; set; }
    public int Agility { get; set; }
    public int Reactions { get; set; }
    public int Balance { get; set; }
    public int ShotPower { get; set; }
    public int Jumping { get; set; }
    public int Stamina { get; set; }
    public int Strength { get; set; }
    public int LongShots { get; set; }
    public int Aggression { get; set; }
    public int Interceptions { get; set; }
    public int Positioning { get; set; }
    public int Vision { get; set; }
    public int Penalties { get; set; }
    public int Composure { get; set; }
    public int Marking { get; set; }
    public int StandingTackle { get; set; }
    public int SlidingTackle { get; set; }
    public int GKDiving { get; set; }
    public int GKHandling { get; set; }
    public int GKKicking { get; set; }
    public int GKPositioning { get; set; }
    public int GKReflexes { get; set; }
}
