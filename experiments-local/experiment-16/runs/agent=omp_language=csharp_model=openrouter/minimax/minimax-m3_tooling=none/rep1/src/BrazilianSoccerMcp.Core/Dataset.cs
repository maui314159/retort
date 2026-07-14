// =============================================================================
// Brazilian Soccer MCP Server
// File: Dataset.cs
// Purpose: In-memory store of all loaded CSV data and the entry point used
//          by the query engine.
// Context: Constructed once at server startup. Holds both match and player
//          collections. Use a DirectoryInfo root or override individual file
//          paths to point at non-default locations.
// =============================================================================

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core;

/// <summary>
/// All loaded data exposed to the query engine. Immutable; queries never
/// mutate the underlying lists.
/// </summary>
public sealed class Dataset
{
    public IReadOnlyList<MatchRecord> Matches { get; }
    public IReadOnlyList<PlayerRecord> Players { get; }

    private Dataset(IReadOnlyList<MatchRecord> matches, IReadOnlyList<PlayerRecord> players)
    {
        Matches = matches;
        Players = players;
    }

    /// <summary>
    /// Load every CSV from <paramref name="root"/> (or the working dir by
    /// default). Pass an explicit root to point at fixtures in tests.
    /// </summary>
    public static Dataset Load(string? root = null)
    {
        root ??= Directory.GetCurrentDirectory();
        string PathFor(string file) => Path.Combine(root, file);

        var matches = new List<MatchRecord>(capacity: 30_000);
        matches.AddRange(BrasileiraoCsvLoader.Load(PathFor(BrasileiraoCsvLoader.DefaultFileName)));
        matches.AddRange(BrazilianCupCsvLoader.Load(PathFor(BrazilianCupCsvLoader.DefaultFileName)));
        matches.AddRange(LibertadoresCsvLoader.Load(PathFor(LibertadoresCsvLoader.DefaultFileName)));
        matches.AddRange(BrFootballCsvLoader.Load(PathFor(BrFootballCsvLoader.DefaultFileName)));
        matches.AddRange(NovoCampeonatoBrasileiroCsvLoader.Load(PathFor(NovoCampeonatoBrasileiroCsvLoader.DefaultFileName)));

        var players = FifaPlayerCsvLoader.Load(PathFor(FifaPlayerCsvLoader.DefaultFileName));

        return new Dataset(matches, players);
    }
}
