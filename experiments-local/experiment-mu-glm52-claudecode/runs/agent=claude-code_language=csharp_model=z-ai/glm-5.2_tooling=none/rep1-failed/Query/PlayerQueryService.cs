// =============================================================================
// File: Query/PlayerQueryService.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Powers the "Player Queries" capability:
//     - SearchPlayers: by name substring, nationality, club, position,
//       minimum FIFA overall
//     - GetTopPlayers: top-N by overall, optionally filtered by nationality
//       and/or club (e.g. highest-rated players at Flamengo)
//     - GetClubRosterSummary: counts + average overall per club for a given
//       nationality (e.g. Brazilian players at Brazilian clubs)
//   Matching is accent- and case-insensitive for names/nationalities/clubs so
//   "são paulo", "Sao Paulo", "SÃO PAULO" all match the same players.
// =============================================================================
namespace BrazilianSoccerMcp.Query;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

public sealed class PlayerQueryService
{
    private readonly SoccerDatabase _db;
    public PlayerQueryService(SoccerDatabase db) => _db = db;

    public List<PlayerResultDto> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int limit = 50)
    {
        var nameKey = NormalizeText(name);
        var natKey = NormalizeText(nationality);
        var clubKey = TeamNameNormalizer.Normalize(club);
        var posKey = NormalizeText(position);

        var results = new List<PlayerResultDto>();
        foreach (var p in _db.Players)
        {
            if (nameKey.Length > 0 && !NormalizeText(p.Name).Contains(nameKey, StringComparison.Ordinal))
                continue;
            if (natKey.Length > 0 && !NormalizeText(p.Nationality).Contains(natKey, StringComparison.Ordinal))
                continue;
            if (clubKey.Length > 0 && !string.Equals(p.ClubNormalized, clubKey, StringComparison.Ordinal))
                continue;
            if (posKey.Length > 0
                && (string.IsNullOrEmpty(p.Position)
                    || !NormalizeText(p.Position).Contains(posKey, StringComparison.Ordinal)))
                continue;
            if (minOverall.HasValue && (!p.Overall.HasValue || p.Overall < minOverall))
                continue;

            results.Add(ToDto(p));
            if (results.Count >= limit) break;
        }
        // Sort by overall desc as a sensible default ordering.
        results.Sort((x, y) => (y.Overall ?? 0).CompareTo(x.Overall ?? 0));
        return results;
    }

    /// <summary>Top-N players by Overall, optionally filtered by nationality / club.</summary>
    public List<PlayerResultDto> GetTopPlayers(int limit, string? nationality = null, string? club = null)
    {
        var natKey = NormalizeText(nationality);
        var clubKey = TeamNameNormalizer.Normalize(club);

        var filtered = new List<PlayerRecord>();
        foreach (var p in _db.Players)
        {
            if (!p.Overall.HasValue) continue;
            if (natKey.Length > 0 && !NormalizeText(p.Nationality).Contains(natKey, StringComparison.Ordinal))
                continue;
            if (clubKey.Length > 0 && !string.Equals(p.ClubNormalized, clubKey, StringComparison.Ordinal))
                continue;
            filtered.Add(p);
        }
        // Take highest-rated N.
        filtered.Sort((x, y) => y.Overall!.Value.CompareTo(x.Overall!.Value));
        var top = filtered.Count > limit ? filtered.GetRange(0, limit) : filtered;
        return top.ConvertAll(ToDto);
    }

    /// <summary>
    /// For players of <paramref name="nationality"/>, summarise per-club roster
    /// sizes and average overall. If <paramref name="brazilianClubsOnly"/> is
    /// true, restrict to clubs whose normalized key matches a team known to the
    /// match data (i.e. a Brazilian club), matching the spec's
    /// "Brazilian players at Brazilian clubs" example.
    /// </summary>
    public List<ClubRosterSummaryDto> GetClubRosterSummary(
        string nationality, bool brazilianClubsOnly = true, int limit = 20)
    {
        var natKey = NormalizeText(nationality);
        if (natKey.Length == 0) return new List<ClubRosterSummaryDto>();

        // Set of normalized team keys known from the match data (Brazilian clubs).
        var knownClubs = brazilianClubsOnly ? new HashSet<string>(_db.AllTeamKeys(), StringComparer.Ordinal) : null;

        var byClub = new Dictionary<string, List<PlayerRecord>>(StringComparer.Ordinal);
        foreach (var p in _db.Players)
        {
            if (natKey.Length > 0 && !NormalizeText(p.Nationality).Contains(natKey, StringComparison.Ordinal))
                continue;
            var clubKey = p.ClubNormalized;
            if (string.IsNullOrEmpty(clubKey)) continue;
            if (knownClubs != null && !knownClubs.Contains(clubKey)) continue;
            if (!byClub.TryGetValue(clubKey, out var list))
            {
                list = new List<PlayerRecord>();
                byClub[clubKey] = list;
            }
            list.Add(p);
        }

        var rows = new List<ClubRosterSummaryDto>(byClub.Count);
        foreach (var kv in byClub)
        {
            var overalls = new List<int>();
            foreach (var p in kv.Value)
                if (p.Overall.HasValue) overalls.Add(p.Overall.Value);
            overalls.Sort();
            double? avg = overalls.Count > 0 ? Math.Round(overalls.Average(), 1) : null;
            int? top = overalls.Count > 0 ? overalls[overalls.Count - 1] : null;
            rows.Add(new ClubRosterSummaryDto
            {
                Club = TeamNameNormalizer.CanonicalDisplay(kv.Key),
                PlayerCount = kv.Value.Count,
                AverageOverall = avg,
                TopOverall = top,
            });
        }
        rows.Sort((x, y) =>
        {
            var c = y.PlayerCount.CompareTo(x.PlayerCount);
            return c != 0 ? c : (y.AverageOverall ?? 0).CompareTo(x.AverageOverall ?? 0);
        });
        if (limit > 0 && rows.Count > limit) rows = rows.GetRange(0, limit);
        return rows;
    }

    internal static PlayerResultDto ToDto(PlayerRecord p) => new()
    {
        Id = p.Id,
        Name = p.Name,
        Age = p.Age,
        Nationality = p.Nationality,
        Overall = p.Overall,
        Potential = p.Potential,
        Club = p.Club,
        Position = p.Position,
        JerseyNumber = p.JerseyNumber,
        PreferredFoot = p.PreferredFoot,
    };

    private static string NormalizeText(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return "";
        return Data.TeamNameNormalizer.RemoveDiacritics(s).ToLowerInvariant().Trim();
    }
}
