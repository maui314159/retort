// =============================================================================
// BrazilianSoccerMcp - Data Models
// -----------------------------------------------------------------------------
// Context: This MCP server exposes a knowledge-graph style query interface over
// six Kaggle Brazilian-soccer datasets (match results + FIFA players). These
// models are the in-memory representation loaded once at startup and queried by
// the MCP tools. Matches are normalized so team names from different files
// (state-suffixed, accented, full-name variants) collapse to one canonical key.
// =============================================================================

namespace BrazilianSoccerMcp.Data;

/// <summary>Display-name candidate for a canonical team key (used at load time).</summary>
public readonly record struct DisplayCandidate(string Name, int Accents, int Len);

/// <summary>Normalized in-memory representation of a single match from any source file.</summary>
public sealed record Match
{
    public string Competition { get; init; } = "";
    public DateTime Date { get; init; }
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public string HomeKey { get; init; } = "";
    public string AwayKey { get; init; } = "";
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    public int Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? Arena { get; init; }
    public string Source { get; init; } = "";

    public bool IsHomeWin => HomeGoals > AwayGoals;
    public bool IsAwayWin => AwayGoals > HomeGoals;
    public bool IsDraw => HomeGoals == AwayGoals;
    public int GoalDifference => Math.Abs(HomeGoals - AwayGoals);
}

/// <summary>Normalized in-memory representation of a FIFA player row.</summary>
public sealed record Player
{
    public int Id { get; init; }
    public string Name { get; init; } = "";
    public int Age { get; init; }
    public string Nationality { get; init; } = "";
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = "";
    public string Position { get; init; } = "";
    public int? JerseyNumber { get; init; }
    public string? Value { get; init; }
    public string? Wage { get; init; }
}

/// <summary>Aggregated win/draw/loss + goals tally for a team over a set of matches.</summary>
public sealed record TeamStat
{
    public string Team { get; init; } = "";
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches * 100.0;
}
