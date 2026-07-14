using BrazilianSoccerMCP.Models;

namespace BrazilianSoccerMCP.Services;

/// <summary>
/// Player query service: search by name, nationality, club, position, rating.
/// </summary>
public class PlayerService
{
    private readonly List<Player> _players;

    public PlayerService(List<Player> players) => _players = players;

    /// <summary>
    /// Search players by various criteria.
    /// </summary>
    public List<Player> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minRating = null,
        int? maxRating = null,
        int? minAge = null,
        int? maxAge = null,
        string? sortBy = null,
        bool descending = true,
        int limit = 100)
    {
        var query = _players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
            query = query.Where(p =>
                p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(nationality))
            query = query.Where(p =>
                p.Nationality.Equals(nationality, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(club))
            query = query.Where(p =>
                p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p =>
                p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));

        if (minRating.HasValue)
            query = query.Where(p => p.Overall >= minRating.Value);
        if (maxRating.HasValue)
            query = query.Where(p => p.Overall <= maxRating.Value);

        if (minAge.HasValue)
            query = query.Where(p => p.Age >= minAge.Value);
        if (maxAge.HasValue)
            query = query.Where(p => p.Age <= maxAge.Value);

        query = (sortBy?.ToLowerInvariant()) switch
        {
            "overall" => descending ? query.OrderByDescending(p => p.Overall) : query.OrderBy(p => p.Overall),
            "potential" => descending ? query.OrderByDescending(p => p.Potential) : query.OrderBy(p => p.Potential),
            "age" => descending ? query.OrderByDescending(p => p.Age) : query.OrderBy(p => p.Age),
            "name" => descending ? query.OrderByDescending(p => p.Name) : query.OrderBy(p => p.Name),
            _ => descending ? query.OrderByDescending(p => p.Overall) : query.OrderBy(p => p.Overall),
        };

        return query.Take(limit).ToList();
    }

    /// <summary>
    /// Get player by name (exact or fuzzy match, returns best match).
    /// </summary>
    public Player? GetPlayerByName(string name)
    {
        // Try exact match first
        var exact = _players.FirstOrDefault(p =>
            p.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
        if (exact != null) return exact;

        // Try contains
        var contains = _players
            .Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .FirstOrDefault();
        return contains;
    }

    /// <summary>
    /// Get top players at a club.
    /// </summary>
    public List<Player> GetTopPlayersByClub(string club, int limit = 20)
    {
        return _players
            .Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Get Brazilian players by position.
    /// </summary>
    public List<Player> GetBrazilianPlayersByPosition(string? position = null, int limit = 100)
    {
        var query = _players.Where(p =>
            p.Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p =>
                p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));

        return query
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Get club summary: player count, avg rating, top players.
    /// </summary>
    public ClubSummary? GetClubSummary(string club)
    {
        var players = _players
            .Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
            .ToList();

        if (players.Count == 0) return null;

        return new ClubSummary
        {
            Club = players.First().Club,
            PlayerCount = players.Count,
            AverageRating = Math.Round(players.Average(p => p.Overall), 1),
            TopPlayers = players.OrderByDescending(p => p.Overall).Take(5).ToList(),
            Positions = players.GroupBy(p => p.Position)
                .OrderByDescending(g => g.Count())
                .Select(g => $"{g.Key}({g.Count()})")
                .ToList(),
        };
    }
}

public class ClubSummary
{
    public string Club { get; set; } = "";
    public int PlayerCount { get; set; }
    public double AverageRating { get; set; }
    public List<Player> TopPlayers { get; set; } = new();
    public List<string> Positions { get; set; } = new();
}