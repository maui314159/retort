// BrazilianSoccerMcp.Core - Facade.
// Combines the data loaders and query service into a single object that the
// MCP server and tests construct with a data directory path.
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Services;

namespace BrazilianSoccerMcp.Core;

/// <summary>
/// Loads all Brazilian soccer datasets from a directory and exposes the
/// <see cref="SoccerQueryService"/> for querying them.
/// </summary>
public sealed class BrazilianSoccerData
{
    public BrazilianSoccerData(string dataDirectory)
    {
        DataDirectory = dataDirectory;
        var matchLoader = new MatchDataLoader();
        var playerLoader = new PlayerDataLoader();
        Matches = matchLoader.LoadAll(dataDirectory);
        Players = playerLoader.Load(dataDirectory);
        Query = new SoccerQueryService(Matches, Players);
    }

    public string DataDirectory { get; }
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }
    public SoccerQueryService Query { get; }
}
