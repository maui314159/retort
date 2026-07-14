// <copyright file="TeamStatistics.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Team statistics aggregates.
// </copyright>
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Aggregated statistics for a team over a given set of matches.
/// </summary>
public sealed class TeamStatistics
{
    /// <summary>
    /// Team name.
    /// </summary>
    public string Team { get; init; } = string.Empty;

    /// <summary>
    /// Season filter, if any.
    /// </summary>
    public int? Season { get; init; }

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
    /// Total goals scored.
    /// </summary>
    public int GoalsFor { get; init; }

    /// <summary>
    /// Total goals conceded.
    /// </summary>
    public int GoalsAgainst { get; init; }

    /// <summary>
    /// Win rate as a percentage (0-100).
    /// </summary>
    public double WinRate => Matches == 0 ? 0 : 100.0 * Wins / Matches;

    /// <summary>
    /// Average goals scored per match.
    /// </summary>
    public double GoalsForPerMatch => Matches == 0 ? 0 : 1.0 * GoalsFor / Matches;

    /// <summary>
    /// Average goals conceded per match.
    /// </summary>
    public double GoalsAgainstPerMatch => Matches == 0 ? 0 : 1.0 * GoalsAgainst / Matches;
}

/// <summary>
/// Home/away split for team statistics.
/// </summary>
public sealed class TeamVenueStatistics
{
    public string Team { get; init; } = string.Empty;
    public TeamStatistics Home { get; init; } = new();
    public TeamStatistics Away { get; init; } = new();
    public TeamStatistics Overall { get; init; } = new();
}
