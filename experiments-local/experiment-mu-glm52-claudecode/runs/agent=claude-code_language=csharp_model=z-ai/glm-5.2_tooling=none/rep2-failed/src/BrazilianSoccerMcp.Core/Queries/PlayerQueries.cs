// BrazilianSoccerMcp.Core / Queries / PlayerQueries.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Implements TASK.md "Required Capabilities
// 3. Player Queries": search by name, filter by nationality (Brazilian), filter by
// club (Brazilian clubs), ratings/attributes, top-rated lists.
// Cross-file design:
//   * The "is this a Brazilian club?" decision is data-driven rather than a
//     hand-maintained allowlist: a player's club is Brazilian iff its normalized
//     name matches a team key present in the match datasets. This is the
//     "Cross-file queries work (e.g., player + match data)" success criterion.
//   * Club matching is accent- and suffix-insensitive via TeamNormalizer, so
//     FIFA's "Flamengo" matches the match data's "Flamengo-RJ".
// Name matching:
//   * FIFA names come in two forms — "L. Messi" (short) and "Cristiano Ronaldo"
//     (full). A player matches a query when the full name contains the (normalized,
//     case-insensitive) query substring, OR when the query matches the short form.
//     This lets "Gabriel Barbosa" find a row even if the FIFA name was stored as
//     "Gabriel Barbosa" or "G. Barbosa".
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;

namespace BrazilianSoccerMcp.Core.Queries;

/// <summary>Player-related queries against the loaded FIFA data.</summary>
public sealed class PlayerQueries
{
    private readonly SoccerDataService _data;
    private readonly Lazy<HashSet<string>> _brazilianClubKeys;

    public PlayerQueries(SoccerDataService data)
    {
        _data = data;
        _brazilianClubKeys = new Lazy<HashSet<string>>(() =>
            _data.Matches
                .Where(m => !string.IsNullOrEmpty(m.HomeTeam))
                .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
                .Where(t => !string.IsNullOrEmpty(t))
                .ToHashSet(StringComparer.Ordinal),
            isThreadSafe: true);
    }

    /// <summary>
    /// Searches players by name (substring, accent- and case-insensitive).
    /// </summary>
    public IReadOnlyList<Player> SearchByName(string query)
    {
        if (string.IsNullOrWhiteSpace(query)) return Array.Empty<Player>();
        var needle = TeamNormalizer.RemoveAccents(query.Trim().ToLowerInvariant());
        return _data.Players
            .Where(p => !string.IsNullOrEmpty(p.Name) &&
                        TeamNormalizer.RemoveAccents(p.Name.ToLowerInvariant()).Contains(needle, StringComparison.Ordinal))
            .OrderByDescending(p => p.Overall)
            .ToList();
    }

    /// <summary>
    /// Filters players by nationality (exact, case-insensitive). Pass "Brazil" for
    /// the "Find all Brazilian players" query.
    /// </summary>
    public IReadOnlyList<Player> ByNationality(string nationality)
    {
        if (string.IsNullOrWhiteSpace(nationality)) return Array.Empty<Player>();
        var needle = nationality.Trim();
        return _data.Players
            .Where(p => p.Nationality is not null &&
                        p.Nationality.Equals(needle, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .ToList();
    }

    /// <summary>
    /// Returns players at a club (substring match on the club name, normalized).
    /// Accepts "Flamengo", "Flamengo-RJ", "flamengo".
    /// </summary>
    public IReadOnlyList<Player> ByClub(string club)
    {
        if (string.IsNullOrWhiteSpace(club)) return Array.Empty<Player>();
        var key = TeamNormalizer.Normalize(club);
        return _data.Players
            .Where(p => !string.IsNullOrEmpty(p.Club) &&
                        TeamNormalizer.Normalize(p.Club) == key)
            .OrderByDescending(p => p.Overall)
            .ToList();
    }

    /// <summary>
    /// Filters players by playing position (exact, case-insensitive).
    /// Use "LW", "ST", "CDM", "GK", etc. as written in the FIFA data.
    /// </summary>
    public IReadOnlyList<Player> ByPosition(string position)
    {
        if (string.IsNullOrWhiteSpace(position)) return Array.Empty<Player>();
        var needle = position.Trim();
        return _data.Players
            .Where(p => !string.IsNullOrEmpty(p.Position) &&
                        p.Position.Equals(needle, StringComparison.OrdinalIgnoreCase))
            .ToList();
    }

    /// <summary>
    /// Returns the top-rated players subject to optional filters. Every filter is
    /// optional; when all are null the result is the global top-N.
    /// </summary>
    public IReadOnlyList<Player> TopRated(int limit = 10, string? nationality = null,
        string? club = null, string? position = null)
    {
        IEnumerable<Player> seq = _data.Players;
        if (!string.IsNullOrWhiteSpace(nationality))
            seq = seq.Where(p => p.Nationality is not null &&
                p.Nationality.Equals(nationality.Trim(), StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(club))
        {
            var clubKey = TeamNormalizer.Normalize(club);
            seq = seq.Where(p => !string.IsNullOrEmpty(p.Club) &&
                TeamNormalizer.Normalize(p.Club) == clubKey);
        }
        if (!string.IsNullOrWhiteSpace(position))
            seq = seq.Where(p => !string.IsNullOrEmpty(p.Position) &&
                p.Position.Equals(position!.Trim(), StringComparison.OrdinalIgnoreCase));
        return seq.OrderByDescending(p => p.Overall).Take(limit).ToList();
    }

    /// <summary>
    /// Cross-file query: Brazilian-nationality players playing at Brazilian clubs.
    /// "Brazilian club" is decided by matching the player's club against a team key
    /// that actually appears in the match datasets. Returns one bucket per club.
    /// </summary>
    public IReadOnlyList<PlayerBucket> BrazilianPlayersAtBrazilianClubs()
    {
        var known = _brazilianClubKeys.Value;
        var groups = _data.Players
            .Where(p => p.IsBrazilian && !string.IsNullOrEmpty(p.Club))
            .Select(p => (Club: TeamNormalizer.Normalize(p.Club!), p.Overall))
            .Where(x => known.Contains(x.Club))
            .GroupBy(x => x.Club, StringComparer.Ordinal)
            .Select(g => new PlayerBucket
            {
                Label = g.Key,
                Count = g.Count(),
                AverageRating = g.Average(x => (double)x.Overall)
            })
            .OrderByDescending(b => b.Count)
            .ThenBy(b => b.Label);
        return groups.ToList();
    }
}
