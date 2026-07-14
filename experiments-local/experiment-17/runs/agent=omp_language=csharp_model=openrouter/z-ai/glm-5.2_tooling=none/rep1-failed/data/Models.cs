// ============================================================================
// File: Data/Models.cs
// ----------------------------------------------------------------------------
// Context: Core domain records for the Brazilian Soccer MCP server.
//
// A single `SoccerMatch` record unifies all five match CSV files so that
// match / team / competition / statistical queries can be answered from one
// in-memory collection regardless of source file. `SoccerPlayer` holds the
// subset of FIFA columns we expose.
//
// Team names are kept both raw (for display) and pre-normalized into a
// `TeamKey` (Bare key + optional state/country suffix) for cross-dataset
// matching. See TeamNameNormalizer.cs.
// ============================================================================

using CsvHelper.Configuration.Attributes;

namespace BrazilianSoccerMcp.Data;

/// <summary>Canonical competitions recognised by the server.</summary>
public static class Competitions
{
    public const string Brasileirao = "Brasileirão";
    public const string BrasileiraoHistorical = "Brasileirão (2003-2019)";
    public const string CopaDoBrasil = "Copa do Brasil";
    public const string Libertadores = "Copa Libertadores";
    public const string BrasileiraoSerieA = "Serie A"; // BR-Football-Dataset tournament label
}

/// <summary>
/// A normalized team identity. <see cref="Bare"/> is the accent-folded,
/// suffix-stripped, hyphen-joined key; <see cref="Suffix"/> is the trailing
/// state/country code (e.g. "MG", "RJ", "URU") when present.
/// </summary>
public readonly record struct TeamKey(string Bare, string? Suffix)
{
    public bool HasSuffix => !string.IsNullOrEmpty(Suffix);

    public string Full => HasSuffix ? $"{Bare}-{Suffix}" : Bare;

    public override string ToString() => Full;
}

/// <summary>One unified match across all source files.</summary>
public sealed record SoccerMatch
{
    public required string Competition { get; init; }
    public string? Source { get; init; }

    public DateTime? Date { get; init; }

    public string HomeTeamRaw { get; init; } = "";
    public string AwayTeamRaw { get; init; } = "";

    public TeamKey HomeKey { get; init; }
    public TeamKey AwayKey { get; init; }

    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }

    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? Stadium { get; init; }

    public int? TotalGoals => (HomeGoals is { } h && AwayGoals is { } a) ? h + a : null;
    public int? GoalDifference => (HomeGoals is { } h && AwayGoals is { } a) ? Math.Abs(h - a) : null;

    /// <summary>Result from the home team's perspective: W / D / L, or null if scores missing.</summary>
    public char? HomeResult => (HomeGoals, AwayGoals) switch
    {
        (int h, int a) when h > a => 'W',
        (int h, int a) when h < a => 'L',
        (int h, int a) when h == a => 'D',
        _ => null
    };
}

/// <summary>Subset of the FIFA player database we expose.</summary>
public sealed class SoccerPlayer
{
    [Name("ID")] public int Id { get; set; }
    public string Name { get; set; } = "";
    public int Age { get; set; }
    public string Nationality { get; set; } = "";
    public int Overall { get; set; }
    public int Potential { get; set; }
    public string Club { get; set; } = "";
    public string Position { get; set; } = "";
    [Name("Jersey Number")] public int? JerseyNumber { get; set; }
    [Name("Preferred Foot")] public string PreferredFoot { get; set; } = "";
    public string Height { get; set; } = "";
    public string Weight { get; set; } = "";

    // Skill ratings (blank for goalkeepers / out-of-position rows).
    public int? Crossing { get; set; }
    public int? Finishing { get; set; }
    public int? Dribbling { get; set; }
    public int? ShortPassing { get; set; }
    public int? LongPassing { get; set; }
    public int? SprintSpeed { get; set; }
    public int? ShotPower { get; set; }
    public int? Stamina { get; set; }
    public int? Strength { get; set; }
    public int? Agility { get; set; }
    public int? Vision { get; set; }
    public int? Composure { get; set; }
    public int? Penalties { get; set; }
}

/// <summary>Win/draw/loss aggregate for a team over a set of matches.</summary>
public sealed record TeamRecord(
    string Team,
    int Matches,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst)
{
    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches;
}
