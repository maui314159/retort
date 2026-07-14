using CsvHelper.Configuration.Attributes;

namespace BrazilianSoccerMCP.Models;

public record FifaPlayer
{
    [Name("ID")]
    public int Id { get; init; }

    [Name("Name")]
    public string Name { get; init; } = "";

    [Name("Age")]
    public int? Age { get; init; }

    [Name("Nationality")]
    public string Nationality { get; init; } = "";

    [Name("Overall")]
    public int Overall { get; init; }

    [Name("Potential")]
    public int Potential { get; init; }

    [Name("Club")]
    public string Club { get; init; } = "";

    [Name("Position")]
    public string Position { get; init; } = "";

    [Name("Jersey Number")]
    public int? JerseyNumber { get; init; }

    [Name("Height")]
    public string Height { get; init; } = "";

    [Name("Weight")]
    public string Weight { get; init; } = "";

    [Name("Preferred Foot")]
    public string PreferredFoot { get; init; } = "";

    [Name("Weak Foot")]
    public int? WeakFoot { get; init; }

    [Name("Skill Moves")]
    public int? SkillMoves { get; init; }

    [Name("Work Rate")]
    public string WorkRate { get; init; } = "";
}