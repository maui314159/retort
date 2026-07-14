// -----------------------------------------------------------------------------
// File: Queries/PlayerQueryService.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Implements the "Player Queries" capability from TASK.md over fifa_data.csv:
//   search by name, filter by nationality (esp. Brazilian), filter by club (esp.
//   Brazilian clubs), filter by position, and rank by FIFA Overall rating.
//   Backs questions like "Who is Gabriel Barbosa?", "Find all Brazilian players",
//   "Who are the highest-rated players at Flamengo?", "all forwards from a club".
//
//   String matching is accent/case-insensitive (reusing TeamName's fold for
//   clubs, and an explicit invariant fold for names/nationality/position) so
//   "neymar" finds "Neymar Jr" and "sao paulo" finds "São Paulo FC". Results are
//   ordered by Overall descending by default (nulls last) so "top players" is the
//   natural reading. The ClubBreakdown helper backs the "players grouped by club"
//   answer format.
// -----------------------------------------------------------------------------

using System.Globalization;
using System.Text;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>FIFA player search and ranking queries.</summary>
public sealed class PlayerQueryService
{
    private readonly SoccerDataStore _store;

    public PlayerQueryService(SoccerDataStore store) => _store = store;

    /// <summary>
    /// Finds players matching every supplied (non-null) filter, ordered by Overall
    /// descending (rating-less players last). <paramref name="name"/> matches a
    /// substring of the player's name; <paramref name="club"/> uses club-name
    /// folding; <paramref name="nationality"/> and <paramref name="position"/>
    /// match a substring of those fields.
    /// </summary>
    public IReadOnlyList<Player> Find(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? limit = null)
    {
        IEnumerable<Player> q = _store.Players;

        if (!string.IsNullOrWhiteSpace(name))
        {
            var key = Fold(name);
            q = q.Where(p => Fold(p.Name).Contains(key, StringComparison.Ordinal));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var key = Fold(nationality);
            q = q.Where(p => Fold(p.Nationality).Contains(key, StringComparison.Ordinal));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            q = q.Where(p => p.Club is not null && TeamName.Matches(p.Club, club));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            var key = Fold(position);
            q = q.Where(p => p.Position is not null
                             && Fold(p.Position).Contains(key, StringComparison.Ordinal));
        }

        if (minOverall is not null)
            q = q.Where(p => p.Overall >= minOverall);

        q = q.OrderByDescending(p => p.Overall ?? int.MinValue)
             .ThenBy(p => p.Name, StringComparer.OrdinalIgnoreCase);

        if (limit is > 0)
            q = q.Take(limit.Value);

        return q.ToList();
    }

    /// <summary>
    /// Groups players by club (after applying the same filters as <see cref="Find"/>),
    /// ordered by player count descending. Backs "Brazilian players at Brazilian
    /// clubs: Flamengo: 8 players (avg rating: 74) ...".
    /// </summary>
    public IReadOnlyList<ClubPlayers> ClubBreakdown(
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? maxClubs = null)
    {
        var matched = Find(
            nationality: nationality, club: club, position: position, minOverall: minOverall);

        var groups = matched
            .Where(p => !string.IsNullOrWhiteSpace(p.Club))
            .GroupBy(p => p.Club!)
            .Select(g => new ClubPlayers
            {
                Club = g.Key,
                Count = g.Count(),
                AverageOverall = g.Where(p => p.Overall is not null)
                                  .Select(p => (double)p.Overall!.Value)
                                  .DefaultIfEmpty(0)
                                  .Average(),
                Players = g.OrderByDescending(p => p.Overall ?? int.MinValue).ToList(),
            })
            .OrderByDescending(c => c.Count)
            .ThenBy(c => c.Club, StringComparer.OrdinalIgnoreCase);

        return (maxClubs is > 0 ? groups.Take(maxClubs.Value) : groups).ToList();
    }

    // Accent-stripping, lowercasing fold for free-text fields.
    private static string Fold(string s)
    {
        var decomposed = s.Trim().ToLowerInvariant().Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(decomposed.Length);
        foreach (var c in decomposed)
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
