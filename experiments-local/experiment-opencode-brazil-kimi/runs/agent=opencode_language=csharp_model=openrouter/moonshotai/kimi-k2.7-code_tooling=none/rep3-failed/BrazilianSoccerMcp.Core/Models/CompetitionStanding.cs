// <copyright file="CompetitionStanding.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - League table model.
// </copyright>
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// A single row in a league table calculated from match results.
/// Brazilian league uses 3 points for a win, 1 point for a draw.
/// </summary>
public sealed class CompetitionStanding
{
    /// <summary>
    /// Team name.
    /// </summary>
    public string Team { get; init; } = string.Empty;

    /// <summary>
    /// Number of matches played.
    /// </summary>
    public int Matches { get; init; }

    /// <summary>
    /// Number of wins.
    /// </summary>
    public int Wins { get; init; }

    /// <summary>
    /// Number of draws.
    /// </summary>
    public int Draws { get; init; }

    /// <summary>
    /// Number of losses.
    /// </summary>
    public int Losses { get; init; }

    /// <summary>
    /// Goals scored.
    /// </summary>
    public int GoalsFor { get; init; }

    /// <summary>
    /// Goals conceded.
    /// </summary>
    public int GoalsAgainst { get; init; }

    /// <summary>
    /// Goal difference.
    /// </summary>
    public int GoalDifference => GoalsFor - GoalsAgainst;

    /// <summary>
    /// Total points.
    /// </summary>
    public int Points => (Wins * 3) + Draws;
}
