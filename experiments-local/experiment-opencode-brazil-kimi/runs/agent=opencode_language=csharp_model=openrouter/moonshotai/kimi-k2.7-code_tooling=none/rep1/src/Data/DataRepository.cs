/*
 * Brazilian Soccer MCP Server - Data Repository
 *
 * Holds the loaded match and player datasets in memory for fast querying.
 */
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

public sealed class DataRepository
{
    private readonly Lazy<IReadOnlyList<MatchRecord>> _matches;
    private readonly Lazy<IReadOnlyList<PlayerRecord>> _players;

    public IReadOnlyList<MatchRecord> Matches => _matches.Value;
    public IReadOnlyList<PlayerRecord> Players => _players.Value;

    public DataRepository(string dataDirectory)
    {
        var loader = new CsvLoader();
        _matches = new Lazy<IReadOnlyList<MatchRecord>>(() => loader.LoadMatches(dataDirectory));
        _players = new Lazy<IReadOnlyList<PlayerRecord>>(() => loader.LoadPlayers(dataDirectory));
    }
}
