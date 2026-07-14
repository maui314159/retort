// Context block
// File: Services/SoccerDataStore.cs
// Purpose: Central in-memory data store for the Brazilian Soccer MCP server. The store
// loads every CSV once (matches + players) and exposes the unified collections plus the
// shared TeamNameNormalizer and DateParser to the query services. Loading happens lazily
// on first access so the MCP server starts quickly and tests can construct the store
// without paying the load cost when they only need the normalizer. A custom data
// directory can be injected for tests.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>In-memory store of all loaded matches and players.</summary>
public sealed class SoccerDataStore
{
    private readonly object _gate = new();
    private List<MatchRecord> _matches = new();
    private List<PlayerRecord> _players = new();
    private bool _matchesLoaded;
    private bool _playersLoaded;

    public TeamNameNormalizer Normalizer { get; } = new();
    public DateParser Dates { get; } = new();
    public DataLoader Loader { get; }

    public SoccerDataStore()
    {
        Loader = new DataLoader(Normalizer, Dates);
    }

    /// <summary>Loads matches if needed and returns the cached list.</summary>
    public IReadOnlyList<MatchRecord> Matches
    {
        get
        {
            lock (_gate)
            {
                if (!_matchesLoaded)
                {
                    _matches = Loader.LoadAllMatches();
                    _matchesLoaded = true;
                }
                return _matches;
            }
        }
    }

    /// <summary>Loads players if needed and returns the cached list.</summary>
    public IReadOnlyList<PlayerRecord> Players
    {
        get
        {
            lock (_gate)
            {
                if (!_playersLoaded)
                {
                    _players = Loader.LoadPlayers();
                    _playersLoaded = true;
                }
                return _players;
            }
        }
    }

    /// <summary>Forces matches to be loaded eagerly (used by tests and warmups).</summary>
    public void EnsureMatchesLoaded() => _ = Matches;

    /// <summary>Forces players to be loaded eagerly.</summary>
    public void EnsurePlayersLoaded() => _ = Players;
}
