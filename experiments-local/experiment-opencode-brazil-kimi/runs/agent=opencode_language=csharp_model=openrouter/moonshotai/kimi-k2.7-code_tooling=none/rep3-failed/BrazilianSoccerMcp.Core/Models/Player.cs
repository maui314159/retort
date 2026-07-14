// <copyright file="Player.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - FIFA player model.
// </copyright>
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Represents a player loaded from the FIFA player database CSV.
/// </summary>
public sealed class Player
{
    /// <summary>
    /// Unique FIFA identifier.
    /// </summary>
    public long Id { get; init; }

    /// <summary>
    /// Player name as reported in the dataset.
    /// </summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>
    /// Player age.
    /// </summary>
    public int? Age { get; init; }

    /// <summary>
    /// Nationality.
    /// </summary>
    public string Nationality { get; init; } = string.Empty;

    /// <summary>
    /// Overall FIFA rating.
    /// </summary>
    public int? Overall { get; init; }

    /// <summary>
    /// Potential FIFA rating.
    /// </summary>
    public int? Potential { get; init; }

    /// <summary>
    /// Current club.
    /// </summary>
    public string Club { get; init; } = string.Empty;

    /// <summary>
    /// Primary playing position.
    /// </summary>
    public string Position { get; init; } = string.Empty;

    /// <summary>
    /// Shirt number.
    /// </summary>
    public string JerseyNumber { get; init; } = string.Empty;

    /// <summary>
    /// Preferred foot.
    /// </summary>
    public string PreferredFoot { get; init; } = string.Empty;
}
