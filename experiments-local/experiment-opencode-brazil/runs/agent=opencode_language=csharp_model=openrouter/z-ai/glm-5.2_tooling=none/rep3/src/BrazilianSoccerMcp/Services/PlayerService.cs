using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Queries over the FIFA player database: search by name, nationality, club
/// and position, with sorting by overall rating.
/// </summary>
public sealed class PlayerService
{
    private readonly IReadOnlyList<PlayerRecord> _players;

    public PlayerService(DataRepository repo)
    {
        _players = repo.Players;
    }

    public IReadOnlyList<PlayerRecord> Search(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int limit = 50)
    {
        var nkey = (name ?? "").Trim();
        var natKey = (nationality ?? "").Trim();
        var clubKey = (club ?? "").Trim();
        var posKey = (position ?? "").Trim();

        var result = new List<PlayerRecord>();
        foreach (var p in _players)
        {
            if (!string.IsNullOrEmpty(nkey) && !p.Name.Contains(nkey, StringComparison.OrdinalIgnoreCase)) continue;
            if (!string.IsNullOrEmpty(natKey) && !p.Nationality.Contains(natKey, StringComparison.OrdinalIgnoreCase)) continue;
            if (!string.IsNullOrEmpty(clubKey) && !p.Club.Contains(clubKey, StringComparison.OrdinalIgnoreCase)) continue;
            if (!string.IsNullOrEmpty(posKey) && !p.Position.Contains(posKey, StringComparison.OrdinalIgnoreCase)) continue;
            if (minOverall.HasValue && p.Overall < minOverall.Value) continue;
            result.Add(p);
        }
        result.Sort((a, b) => b.Overall.CompareTo(a.Overall));
        return result.Take(limit).ToList();
    }

    /// <summary>Aggregate by club for the supplied filter (e.g. Brazilian players at Brazilian clubs).</summary>
    public IReadOnlyList<ClubSummary> GroupByClub(
        string? nationality = null,
        string? clubContains = null,
        int limit = 25)
    {
        var natKey = (nationality ?? "").Trim();
        var clubKey = (clubContains ?? "").Trim();
        var groups = new Dictionary<string, List<PlayerRecord>>(StringComparer.OrdinalIgnoreCase);

        foreach (var p in _players)
        {
            if (!string.IsNullOrEmpty(natKey) && !p.Nationality.Contains(natKey, StringComparison.OrdinalIgnoreCase)) continue;
            if (!string.IsNullOrEmpty(clubKey) && !p.Club.Contains(clubKey, StringComparison.OrdinalIgnoreCase)) continue;
            if (string.IsNullOrEmpty(p.Club)) continue;
            if (!groups.TryGetValue(p.Club, out var list))
            {
                list = new List<PlayerRecord>();
                groups[p.Club] = list;
            }
            list.Add(p);
        }

        return groups
            .Select(g => new ClubSummary(g.Key, g.Value.Count, g.Value.Average(p => p.Overall)))
            .OrderByDescending(s => s.Count)
            .Take(limit)
            .ToList();
    }
}

public sealed record ClubSummary(string Club, int Count, double AverageOverall);
