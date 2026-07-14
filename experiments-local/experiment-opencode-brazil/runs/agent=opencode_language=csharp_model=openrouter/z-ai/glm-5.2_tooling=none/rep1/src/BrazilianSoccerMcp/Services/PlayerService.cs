// Context block
// File: Services/PlayerService.cs
// Purpose: Player-level queries for the Brazilian Soccer MCP server backed by the FIFA
// player dataset. Supports searching by name (contains), nationality, club, position,
// minimum overall rating, and ordering by overall rating. Returns trimmed PlayerRecord
// lists with a configurable top-N so large result sets stay small. Club matching uses
// case-insensitive contains so "Flamengo" matches "Clube de Regatas do Flamengo" style
// entries if present. Brazilian nationality is matched case-insensitively against the
// "Brazil" value used by the FIFA dataset.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Player-level queries.</summary>
public sealed class PlayerService
{
    private readonly SoccerDataStore _store;

    public PlayerService(SoccerDataStore store) => _store = store;

    /// <summary>Searches players with optional filters and returns the top-N by overall rating.</summary>
    public List<PlayerRecord> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int topN = 25)
    {
        var players = _store.Players;
        var result = new List<PlayerRecord>(players.Count);
        foreach (var p in players)
        {
            if (name is not null && !p.Name.Contains(name, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            if (nationality is not null && !p.Nationality.Equals(nationality, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            if (club is not null && !p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            if (position is not null && !p.Position.Equals(position, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            if (minOverall is not null && p.Overall < minOverall)
            {
                continue;
            }
            result.Add(p);
        }
        result.Sort((a, b) =>
        {
            var byOverall = b.Overall.CompareTo(a.Overall);
            if (byOverall != 0) return byOverall;
            return string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase);
        });
        if (topN > 0 && result.Count > topN)
        {
            result.RemoveRange(topN, result.Count - topN);
        }
        return result;
    }

    /// <summary>Counts Brazilian players grouped by club, ordered by count descending.</summary>
    public List<ClubPlayerCount> BrazilianPlayersByClub(int topN = 25)
    {
        var players = _store.Players;
        var grouped = new Dictionary<string, List<PlayerRecord>>(StringComparer.OrdinalIgnoreCase);
        foreach (var p in players)
        {
            if (!p.Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            if (string.IsNullOrWhiteSpace(p.Club))
            {
                continue;
            }
            if (!grouped.TryGetValue(p.Club, out var list))
            {
                list = new List<PlayerRecord>();
                grouped[p.Club] = list;
            }
            list.Add(p);
        }
        var result = grouped.Select(kv => new ClubPlayerCount(kv.Key, kv.Value.Count,
            kv.Value.Average(x => x.Overall))).ToList();
        result.Sort((a, b) =>
        {
            var byCount = b.Count.CompareTo(a.Count);
            if (byCount != 0) return byCount;
            return b.AverageOverall.CompareTo(a.AverageOverall);
        });
        if (topN > 0 && result.Count > topN)
        {
            result.RemoveRange(topN, result.Count - topN);
        }
        return result;
    }
}

/// <summary>Club-level player count aggregate.</summary>
public sealed record ClubPlayerCount(string Club, int Count, double AverageOverall);
