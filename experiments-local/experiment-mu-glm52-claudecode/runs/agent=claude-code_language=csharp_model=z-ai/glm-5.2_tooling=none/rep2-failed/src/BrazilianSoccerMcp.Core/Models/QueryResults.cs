// BrazilianSoccerMcp.Core / Models / QueryResults.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. These are the value-object results the
// query services return and the formatter renders. Keeping them as plain records
// means tests can assert on exact fields rather than scraping formatted text.
// -----------------------------------------------------------------------------

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>Aggregate win/draw/loss + goals for a team across a filtered match set.</summary>
public sealed record TeamRecord
{
    public required string Team { get; init; }
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }

    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches;
    public int GoalDifference => GoalsFor - GoalsAgainst;

    public string Describe() =>
        $"{Matches}M, {Wins}W {Draws}D {Losses}L, GF {GoalsFor} GA {GoalsAgainst} ({(Matches == 0 ? 0 : WinRate * 100):F1}%)";
}

/// <summary>Head-to-head summary between two teams across a match set.</summary>
public sealed record HeadToHead
{
    public required string TeamA { get; init; }
    public required string TeamB { get; init; }
    public int TeamAWins { get; init; }
    public int TeamBWins { get; init; }
    public int Draws { get; init; }
    public int TotalMatches => TeamAWins + TeamBWins + Draws;
}

/// <summary>A single standings row: team + point tally sorted by points desc.</summary>
public sealed record StandingsRow
{
    public int Position { get; set; }
    public required string Team { get; init; }
    public required TeamRecord Record { get; init; }
    public bool IsChampion { get; init; }
}

/// <summary>A single biggest-victory entry, sorted by goal difference descending.</summary>
public sealed record BiggestWin
{
    public DateTime? Date { get; init; }
    public required string Winner { get; init; }
    public required string Loser { get; init; }
    public int WinnerGoals { get; init; }
    public int LoserGoals { get; init; }
    public int GoalDifference => WinnerGoals - LoserGoals;
    public required string Competition { get; init; }
    public int? Season { get; init; }
}

/// <summary>Bucketed player-count + average-rating summary for one club/nationality.</summary>
public sealed record PlayerBucket
{
    public required string Label { get; init; }
    public int Count { get; init; }
    public double AverageRating { get; init; }
}
