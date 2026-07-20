// BrazilianSoccerMcp.Core / Data / SoccerDataService.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. This is the in-memory knowledge surface
// described in TASK.md "Purpose": a single service that loads all six CSVs once
// and exposes them to the query layer and the MCP tools.
// Purpose:
//   * One-shot lazy load with caching so queries are fast (TASK.md "Query
//     Performance": simple <2s, aggregate <5s).
//   * Carries a distinct list per competition + a flat Matches view, plus the
//     player list, so queries can scope to a single file or fan across all.
//   * Provides a helper to find a team's canonical key from a user-supplied
//     (possibly suffixed, possibly accented) team name — the bridge from
//     user-facing strings to normalized keys.
//   * Records load counts + a skipped-row estimate so the MCP `data_summary`
//     tool can report coverage (TASK.md "Data Coverage" success criterion).
// Design notes:
//   * All fields are readonly after first load; thread-safe lazy via Lazy<T>.
//   * The constructor accepts an optional dataRoot so tests (repo-relative) and
//     the server (output-folder-relative) both work without copying CSVs.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>
/// Holds every loaded match and player row, plus derived indexes used by the
/// query services. Loads lazily on first access.
/// </summary>
public sealed class SoccerDataService
{
    private readonly string _dataRoot;
    private readonly Lazy<LoadedData> _data;

    public SoccerDataService(string? dataRoot = null)
    {
        _dataRoot = dataRoot ?? string.Empty;
        _data = new Lazy<LoadedData>(Load, isThreadSafe: true);
    }

    /// <summary>Normalized, queryable match list spanning all five match CSVs.</summary>
    public IReadOnlyList<Match> Matches => _data.Value.Matches;

    /// <summary>FIFA player list.</summary>
    public IReadOnlyList<Player> Players => _data.Value.Players;

    /// <summary>Per-competition partition of the match list.</summary>
    public IReadOnlyDictionary<CompetitionKind, IReadOnlyList<Match>> MatchesByCompetition =>
        _data.Value.ByCompetition;

    /// <summary>Counts per source file (load coverage / data-quality signal).</summary>
    public IReadOnlyDictionary<string, int> LoadCounts => _data.Value.Counts;

    /// <summary>
    /// Resolves a user-supplied team name (possibly suffixed, accented, or in a
    /// different file's naming form) to the SET of canonical team keys that refer
    /// to the same club. Suffix-tolerant: "Flamengo" matches "flamengo-rj"; never
    /// merges distinct same-base clubs (Atlético-MG vs -GO). Returns empty when no
    /// loaded team matches.
    /// </summary>
    public IReadOnlyList<string> ResolveTeamKeys(string? teamQuery)
    {
        if (string.IsNullOrWhiteSpace(teamQuery)) return Array.Empty<string>();
        var queryKey = TeamNormalizer.Normalize(teamQuery);
        if (string.IsNullOrEmpty(queryKey)) return Array.Empty<string>();

        var data = _data.Value;
        var matches = new HashSet<string>(StringComparer.Ordinal);
        foreach (var stored in data.TeamKeys)
        {
            if (TeamNormalizer.SameTeam(stored, queryKey))
                matches.Add(stored);
        }
        return matches.ToList();
    }

    /// <summary>
    /// Returns matches involving any of <paramref name="teamKeys"/> (already
    /// canonicalized) across all competitions, in chronological order.
    /// </summary>
    public IReadOnlyList<Match> MatchesForTeamKeys(IReadOnlyCollection<string> teamKeys)
    {
        if (teamKeys.Count == 0) return Array.Empty<Match>();
        var set = new HashSet<string>(teamKeys, StringComparer.Ordinal);
        return _data.Value.Matches
            .Where(m => set.Contains(m.HomeTeam) || set.Contains(m.AwayTeam))
            .OrderBy(m => m.Date ?? DateTime.MinValue)
            .ToList();
    }

    private LoadedData Load()
    {
        var root = string.IsNullOrEmpty(_dataRoot)
            ? DataLocator.ResolveKagglePath()
            : _dataRoot;

        var brasileirao = CsvLoaders.LoadBrasileirao(Path.Combine(root, DataLocator.Files.Brasileirao));
        var copa = CsvLoaders.LoadCopaDoBrasil(Path.Combine(root, DataLocator.Files.CopaDoBrasil));
        var libertadores = CsvLoaders.LoadLibertadores(Path.Combine(root, DataLocator.Files.Libertadores));
        var historical = CsvLoaders.LoadHistoricalBrasileirao(Path.Combine(root, DataLocator.Files.HistoricalBrasileirao));
        var extended = CsvLoaders.LoadExtended(Path.Combine(root, DataLocator.Files.Extended));
        var players = CsvLoaders.LoadPlayers(Path.Combine(root, DataLocator.Files.FifaPlayers));

        var all = brasileirao
            .Concat(copa)
            .Concat(libertadores)
            .Concat(historical)
            .Concat(extended)
            .OrderBy(m => m.Date ?? DateTime.MinValue)
            .ToList();

        var byCompetition = all.GroupBy(m => m.Competition)
            .ToDictionary(g => g.Key, g => (IReadOnlyList<Match>)g.ToList());

        var counts = new Dictionary<string, int>
        {
            [DataLocator.Files.Brasileirao] = brasileirao.Count,
            [DataLocator.Files.CopaDoBrasil] = copa.Count,
            [DataLocator.Files.Libertadores] = libertadores.Count,
            [DataLocator.Files.HistoricalBrasileirao] = historical.Count,
            [DataLocator.Files.Extended] = extended.Count,
            [DataLocator.Files.FifaPlayers] = players.Count,
        };

        var teamKeys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var m in all)
        {
            if (!string.IsNullOrEmpty(m.HomeTeam)) teamKeys.Add(m.HomeTeam);
            if (!string.IsNullOrEmpty(m.AwayTeam)) teamKeys.Add(m.AwayTeam);
        }

        return new LoadedData(all, players, byCompetition, counts, teamKeys);
    }

    private sealed record LoadedData(
        IReadOnlyList<Match> Matches,
        IReadOnlyList<Player> Players,
        IReadOnlyDictionary<CompetitionKind, IReadOnlyList<Match>> ByCompetition,
        IReadOnlyDictionary<string, int> Counts,
        HashSet<string> TeamKeys);
}
