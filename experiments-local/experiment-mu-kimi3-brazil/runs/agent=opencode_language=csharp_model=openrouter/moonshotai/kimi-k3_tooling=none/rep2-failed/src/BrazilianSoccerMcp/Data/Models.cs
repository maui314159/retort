// Context: Brazilian Soccer MCP Server.
// Unified domain model. All six CSV files are normalized into MatchRecord /
// PlayerRecord so the query engine and knowledge graph work over one schema.
namespace BrazilianSoccerMcp.Data;

/// <summary>Canonical competition names used across the server.</summary>
public static class Competitions
{
    public const string SerieA = "Brasileirão Série A";
    public const string SerieB = "Brasileirão Série B";
    public const string SerieC = "Brasileirão Série C";
    public const string CopaDoBrasil = "Copa do Brasil";
    public const string Libertadores = "Copa Libertadores";

    public static readonly string[] All = [SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores];

    /// <summary>Maps a competition alias (case/diacritic-insensitive) to its canonical name.</summary>
    public static string? Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var key = TeamNameNormalizer.Fold(raw);
        return key switch
        {
            "serie a" or "brasileirao" or "brasileirao serie a" or "campeonato brasileiro"
                or "brasileirao a" or "brazilian serie a" => SerieA,
            "serie b" or "brasileirao serie b" => SerieB,
            "serie c" or "brasileirao serie c" => SerieC,
            "copa do brasil" or "brazilian cup" => CopaDoBrasil,
            "copa libertadores" or "libertadores" or "copa libertadores da america" => Libertadores,
            _ => null,
        };
    }
}

/// <summary>Unified match record across every dataset.</summary>
public sealed record MatchRecord
{
    public required DateOnly Date { get; init; }
    public required string HomeTeamRaw { get; init; }
    public required string AwayTeamRaw { get; init; }
    /// <summary>Canonical identity keys produced by <see cref="TeamNameNormalizer"/>.</summary>
    public required string HomeTeamKey { get; init; }
    public required string AwayTeamKey { get; init; }
    public required int HomeGoals { get; init; }
    public required int AwayGoals { get; init; }
    public required string Competition { get; init; }
    public required int Season { get; init; }
    /// <summary>Round number or cup stage, as present in the source.</summary>
    public string? Round { get; init; }
    /// <summary>Source file short name (e.g. "Brasileirao_Matches").</summary>
    public required string Source { get; init; }

    public bool IsDraw => HomeGoals == AwayGoals;
    public bool HomeWin => HomeGoals > AwayGoals;
    public int GoalMargin => Math.Abs(HomeGoals - AwayGoals);
    public int TotalGoals => HomeGoals + AwayGoals;

    /// <summary>Dedup key: same fixture, same day, same competition.</summary>
    public string DedupKey => $"{Date:yyyy-MM-dd}|{HomeTeamKey}|{AwayTeamKey}|{Competition}";
}

/// <summary>FIFA player database row (subset of columns relevant to queries).</summary>
public sealed record PlayerRecord
{
    public required int Id { get; init; }
    public required string Name { get; init; }
    public int Age { get; init; }
    public string? Nationality { get; init; }
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public int? Finishing { get; init; }
    public int? Dribbling { get; init; }
    public int? ShortPassing { get; init; }
    public int? SprintSpeed { get; init; }
}

/// <summary>Aggregate W/D/L record with goals.</summary>
public sealed class TeamRecord
{
    public int Played { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Played == 0 ? 0 : (double)Wins / Played * 100.0;
}

/// <summary>Head-to-head summary between two teams.</summary>
public sealed record HeadToHead(
    string TeamA, string TeamB,
    int WinsA, int WinsB, int Draws,
    int GoalsA, int GoalsB,
    IReadOnlyList<MatchRecord> Matches);
