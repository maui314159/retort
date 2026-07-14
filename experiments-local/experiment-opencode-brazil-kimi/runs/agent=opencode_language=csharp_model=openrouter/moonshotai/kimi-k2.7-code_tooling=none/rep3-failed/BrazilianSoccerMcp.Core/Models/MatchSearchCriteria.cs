// <copyright file="MatchSearchCriteria.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Search criteria for matches.
// </copyright>
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Filter criteria for match queries.
/// </summary>
public sealed class MatchSearchCriteria
{
    /// <summary>
    /// Team to search for (home, away or either).
    /// </summary>
    public string? Team { get; init; }

    /// <summary>
    /// Specific opponent. When set, only matches between Team and Opponent are returned.
    /// </summary>
    public string? Opponent { get; init; }

    /// <summary>
    /// Start of date range.
    /// </summary>
    public DateTime? StartDate { get; init; }

    /// <summary>
    /// End of date range.
    /// </summary>
    public DateTime? EndDate { get; init; }

    /// <summary>
    /// Competition name filter.
    /// </summary>
    public string? Competition { get; init; }

    /// <summary>
    /// Season / year filter.
    /// </summary>
    public int? Season { get; init; }

    /// <summary>
    /// Round / stage filter.
    /// </summary>
    public string? Round { get; init; }

    /// <summary>
    /// Maximum number of matches to return.
    /// </summary>
    public int? Limit { get; init; }

    /// <summary>
    /// Sort order. "date_desc" (default), "date_asc" or "goal_diff_desc".
    /// </summary>
    public string? SortBy { get; init; }
}
