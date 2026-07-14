// <copyright file="PlayerSearchCriteria.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Search criteria for players.
// </copyright>
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Filter criteria for player queries.
/// </summary>
public sealed class PlayerSearchCriteria
{
    /// <summary>
    /// Substring match against player name.
    /// </summary>
    public string? Name { get; init; }

    /// <summary>
    /// Nationality filter.
    /// </summary>
    public string? Nationality { get; init; }

    /// <summary>
    /// Club filter.
    /// </summary>
    public string? Club { get; init; }

    /// <summary>
    /// Position filter.
    /// </summary>
    public string? Position { get; init; }

    /// <summary>
    /// Minimum overall rating.
    /// </summary>
    public int? MinOverall { get; init; }

    /// <summary>
    /// Sort order. "overall_desc" (default) or "name_asc".
    /// </summary>
    public string? SortBy { get; init; }

    /// <summary>
    /// Maximum results to return.
    /// </summary>
    public int? Limit { get; init; }
}
