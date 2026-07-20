// =============================================================================
// File: Query/QueryResults.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Plain serialisable DTOs returned by the query services and the MCP tools.
//   These are intentionally POCO-style (public get/set properties) so the MCP
//   SDK's JsonSerializer can surface them as structured tool output without
//   per-type configuration.
// =============================================================================
namespace BrazilianSoccerMcp.Query;

using System.Collections.Generic;

/// <summary>One match in a search result, with human-readable display fields.</summary>
public sealed class MatchResultDto
{
    public string Competition { get; set; } = "";
    public string HomeTeam { get; set; } = "";
    public string AwayTeam { get; set; } = "";
    public int? HomeGoal { get; set; }
    public int? AwayGoal { get; set; }
    public string? Date { get; set; }        // ISO yyyy-MM-dd
    public int? Season { get; set; }
    public string? Round { get; set; }
    public string? Stage { get; set; }
    public string? Arena { get; set; }
    public string? SourceFile { get; set; }
    public string? Winner { get; set; }      // "home"/"away"/"draw"
}

/// <summary>Aggregated team statistics for a filtered slice of matches.</summary>
public sealed class TeamStatsDto
{
    public string Team { get; set; } = "";
    public string? Competition { get; set; }
    public int? Season { get; set; }
    public string? Venue { get; set; }       // "home"/"away"/"both"
    public int Matches { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public double WinRate { get; set; }
    public double GoalsForAverage { get; set; }
}

/// <summary>Head-to-head comparison between two teams.</summary>
public sealed class HeadToHeadDto
{
    public string TeamA { get; set; } = "";
    public string TeamB { get; set; } = "";
    public int Matches { get; set; }
    public int TeamAWins { get; set; }
    public int TeamBWins { get; set; }
    public int Draws { get; set; }
    public int TeamAGoals { get; set; }
    public int TeamBGoals { get; set; }
    public List<MatchResultDto> RecentMatches { get; set; } = new();
}

/// <summary>One player in a search/ranking result.</summary>
public sealed class PlayerResultDto
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public int? Age { get; set; }
    public string Nationality { get; set; } = "";
    public int? Overall { get; set; }
    public int? Potential { get; set; }
    public string Club { get; set; } = "";
    public string? Position { get; set; }
    public int? JerseyNumber { get; set; }
    public string? PreferredFoot { get; set; }
}

/// <summary>Standing row for a competition + season.</summary>
public sealed class StandingRowDto
{
    public int Position { get; set; }
    public string Team { get; set; } = "";
    public int Matches { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int GoalDifference { get; set; }
    public int Points { get; set; }
}

/// <summary>Aggregate goals/win-rate stats for a competition slice.</summary>
public sealed class GoalsStatsDto
{
    public string? Competition { get; set; }
    public int? Season { get; set; }
    public int Matches { get; set; }
    public int TotalGoals { get; set; }
    public double AverageGoalsPerMatch { get; set; }
    public double HomeWinRate { get; set; }
    public double AwayWinRate { get; set; }
    public double DrawRate { get; set; }
}

/// <summary>One big victory in the dataset, ranked by goal margin.</summary>
public sealed class BiggestWinDto
{
    public string? Date { get; set; }
    public string Competition { get; set; } = "";
    public string HomeTeam { get; set; } = "";
    public string AwayTeam { get; set; } = "";
    public int HomeGoal { get; set; }
    public int AwayGoal { get; set; }
    public int Margin { get; set; }
    public int? Season { get; set; }
}

/// <summary>Summary of how many players a club has from a nationality.</summary>
public sealed class ClubRosterSummaryDto
{
    public string Club { get; set; } = "";
    public int PlayerCount { get; set; }
    public double? AverageOverall { get; set; }
    public int? TopOverall { get; set; }
}
