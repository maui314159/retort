// <copyright file="SoccerDataContext.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - In-memory data context used by the query services.
// </copyright>
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>
/// Holds the loaded match and player datasets in memory.
/// </summary>
public sealed class SoccerDataContext
{
    private readonly Lazy<IReadOnlyList<SoccerMatch>> _matches;
    private readonly Lazy<IReadOnlyList<Player>> _players;

    public SoccerDataContext(CsvDataLoader loader)
    {
        ArgumentNullException.ThrowIfNull(loader);

        _matches = new Lazy<IReadOnlyList<SoccerMatch>>(() => loader.LoadMatches());
        _players = new Lazy<IReadOnlyList<Player>>(() => loader.LoadPlayers());
    }

    /// <summary>
    /// All normalized soccer matches loaded from the CSVs.
    /// </summary>
    public IReadOnlyList<SoccerMatch> Matches => _matches.Value;

    /// <summary>
    /// All normalized players loaded from the FIFA CSV.
    /// </summary>
    public IReadOnlyList<Player> Players => _players.Value;
}
