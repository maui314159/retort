using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;

namespace BrazilianSoccerMcp.Services;

/// <summary>Player search and aggregation over the FIFA player dataset.</summary>
public sealed class PlayerQueryService
{
    private readonly KnowledgeGraph _graph;

    public PlayerQueryService(KnowledgeGraph graph) => _graph = graph;

    public sealed record PlayerFilter
    {
        public string? Name { get; init; }
        public string? Nationality { get; init; }
        public string? Club { get; init; }
        public string? Position { get; init; }
        public int? MinOverall { get; init; }
        public bool ForwardsOnly { get; init; }
        public int Limit { get; init; } = 15;
    }

    /// <summary>Searches players by name/nationality/club/position, best-rated first.</summary>
    public IReadOnlyList<Player> Search(PlayerFilter filter)
    {
        var query = _graph.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(filter.Name))
        {
            var needle = TeamNameNormalizer.Normalize(filter.Name);
            query = query.Where(p => TeamNameNormalizer.Normalize(p.Name).Contains(needle, StringComparison.Ordinal));
        }

        if (!string.IsNullOrWhiteSpace(filter.Nationality))
        {
            var needle = TeamNameNormalizer.Normalize(filter.Nationality);
            query = query.Where(p => p.Nationality is not null
                                     && TeamNameNormalizer.Normalize(p.Nationality) == needle);
        }

        if (!string.IsNullOrWhiteSpace(filter.Club))
        {
            var canon = TeamNameNormalizer.CanonKey(filter.Club);
            // Prefer the exact canonical club ("Santos") over substring hits
            // ("Santos Laguna"); only fall back to substring when nothing matches.
            if (_graph.PlayersByClubKey.ContainsKey(canon))
            {
                query = query.Where(p => p.ClubKey == canon);
            }
            else
            {
                var needle = TeamNameNormalizer.Normalize(filter.Club);
                query = query.Where(p => p.Club is not null
                                         && TeamNameNormalizer.Normalize(p.Club).Contains(needle, StringComparison.Ordinal));
            }
        }

        if (!string.IsNullOrWhiteSpace(filter.Position))
        {
            var pos = filter.Position.Trim();
            query = query.Where(p => string.Equals(p.Position, pos, StringComparison.OrdinalIgnoreCase));
        }

        if (filter.ForwardsOnly)
            query = query.Where(p => p.IsForward);

        if (filter.MinOverall is { } min)
            query = query.Where(p => p.Overall >= min);

        return query
            .OrderByDescending(p => p.Overall ?? 0)
            .ThenBy(p => p.Name, StringComparer.OrdinalIgnoreCase)
            .Take(filter.Limit <= 0 ? 15 : Math.Min(filter.Limit, 100_000))
            .ToList();
    }

    /// <summary>Counts players matching the filter without the result cap.</summary>
    public int Count(PlayerFilter filter) =>
        Search(filter with { Limit = int.MaxValue }).Count;

    /// <summary>
    /// Players of a club (matched via the same team normalization used for match data),
    /// highest rated first.
    /// </summary>
    public IReadOnlyList<Player> GetClubPlayers(string clubQuery, int limit, out string? note)
    {
        note = null;
        var key = TeamNameNormalizer.CanonKey(clubQuery);

        if (!_graph.PlayersByClubKey.TryGetValue(key, out var players))
        {
            // Fall back to a substring match over club names.
            var needle = TeamNameNormalizer.Normalize(clubQuery);
            players = _graph.Players
                .Where(p => p.Club is not null
                            && TeamNameNormalizer.Normalize(p.Club).Contains(needle, StringComparison.Ordinal))
                .OrderByDescending(p => p.Overall ?? 0)
                .ToList();
        }

        if (players.Count == 0)
        {
            var available = GetBrazilianClubSummary(8)
                .Select(c => $"{c.Club} ({c.Count})");
            note = $"No players found for club '{clubQuery}'. Brazilian clubs present in the FIFA file include: "
                   + string.Join(", ", available) + ".";
            return Array.Empty<Player>();
        }

        return players.Take(Math.Clamp(limit, 1, 200)).ToList();
    }

    /// <summary>Highest-rated players, optionally filtered by nationality/position.</summary>
    public IReadOnlyList<Player> GetTopPlayers(string? nationality = null, string? position = null, int limit = 10) =>
        Search(new PlayerFilter { Nationality = nationality, Position = position, Limit = limit });

    /// <summary>Per-club summary of Brazilian players at Brazilian clubs.</summary>
    public IReadOnlyList<(string Club, int Count, double AvgOverall)> GetBrazilianClubSummary(int limit = 10) =>
        _graph.PlayersByClubKey
            .Where(kv => _graph.Teams.ContainsKey(kv.Key))
            .Select(kv => (
                Club: kv.Value[0].Club!,
                Count: kv.Value.Count(p => string.Equals(p.Nationality, "Brazil", StringComparison.OrdinalIgnoreCase)),
                Avg: kv.Value.Where(p => string.Equals(p.Nationality, "Brazil", StringComparison.OrdinalIgnoreCase))
                             .Select(p => (double)(p.Overall ?? 0))
                             .DefaultIfEmpty(0)
                             .Average()))
            .Where(x => x.Count > 0)
            .OrderByDescending(x => x.Count)
            .ThenByDescending(x => x.Avg)
            .ThenBy(x => x.Club, StringComparer.Ordinal)
            .Take(limit)
            .ToList();
}
