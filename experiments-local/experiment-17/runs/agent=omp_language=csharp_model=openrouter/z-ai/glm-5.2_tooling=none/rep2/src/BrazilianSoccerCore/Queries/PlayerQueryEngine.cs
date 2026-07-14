using BrazilianSoccerCore.Data;
using BrazilianSoccerCore.Models;

namespace BrazilianSoccerCore.Queries;

/// <summary>Queries over the FIFA player dataset.</summary>
public sealed class PlayerQueryEngine
{
    private readonly IReadOnlyList<Player> _players;

    public PlayerQueryEngine(IReadOnlyList<Player> players) => _players = players;

    /// <summary>Search players by name (substring, accent-insensitive).</summary>
    public List<Player> SearchByName(string name, int limit = 50)
    {
        var key = TeamNormalizer.Key(name);
        return _players
            .Where(p => TeamNormalizer.Key(p.Name).Contains(key, StringComparison.Ordinal))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    /// <summary>Filter by nationality, club, and/or position; sorted by overall desc.</summary>
    public List<Player> SearchPlayers(
        string? nationality = null,
        string? club = null,
        string? position = null,
        int minOverall = 0,
        int limit = 50)
    {
        var q = _players.AsEnumerable();

        if (nationality is not null)
        {
            var nKey = TeamNormalizer.Key(nationality);
            q = q.Where(p => TeamNormalizer.Key(p.Nationality) == nKey);
        }

        if (club is not null)
        {
            var cKey = TeamNormalizer.Key(club);
            q = q.Where(p => TeamNormalizer.Key(p.Club).Contains(cKey, StringComparison.Ordinal));
        }

        // Position: match grouping (e.g. "forward" matches ST, LW, RW, CF, etc.)
        if (position is not null)
            q = q.Where(p => PositionMatches(p.Position, position));

        q = q.Where(p => p.Overall >= minOverall);

        return q.OrderByDescending(p => p.Overall).ThenBy(p => p.Name).Take(limit).ToList();
    }

    /// <summary>Top-rated players overall, optionally filtered by nationality/club.</summary>
    public List<Player> TopRated(int limit = 10, string? nationality = null, string? club = null)
        => SearchPlayers(nationality, club, null, 0, limit);

    /// <summary>
    /// Group Brazilian players by their (Brazilian) club with counts and average rating.
    /// </summary>
    public List<(string Club, int Count, double AvgRating)> BrazilianPlayersAtBrazilianClubs()
    {
        // Brazilian clubs: a known set of major Brazilian club name fragments.
        var brazilianClubs = new[]
        {
            "Flamengo","Palmeiras","Corinthians","São Paulo","Santos","Fluminense","Vasco",
            "Grêmio","Internacional","Cruzeiro","Atlético Mineiro","Athletico","Botafogo",
            "Bahia","Fortaleza","Ceará","Sport","Coritiba","Chapecoense","Avaí","Figueirense",
            "Goiás","Vitória","Ponte Preta","América-MG","América-RJ","Athletico-PR","Atlético-GO"
        };

        var brazilKey = TeamNormalizer.Key("Brazil");
        var players = _players.Where(p => TeamNormalizer.Key(p.Nationality) == brazilKey);

        var result = new List<(string Club, int Count, double AvgRating)>();
        foreach (var clubFragment in brazilianClubs)
        {
            var cKey = TeamNormalizer.Key(clubFragment);
            var members = players.Where(p => TeamNormalizer.Key(p.Club).Contains(cKey, StringComparison.Ordinal)).ToList();
            if (members.Count == 0) continue;
            var avg = members.Average(p => p.Overall);
            // Use the actual club string from the first member for display.
            var display = members[0].Club;
            result.Add((display, members.Count, Math.Round(avg, 1)));
        }

        return result.OrderByDescending(r => r.Count).ToList();
    }

    /// <summary>Position grouping: "forward", "midfielder", "defender", "goalkeeper".</summary>
    public static bool PositionMatches(string playerPosition, string requested)
    {
        var pos = playerPosition.ToUpperInvariant();
        var req = requested.Trim().ToUpperInvariant();
        return req switch
        {
            "FORWARD" or "STRIKER" => pos is "ST" or "CF" or "LS" or "RS" or "LW" or "RW" or "LF" or "RF",
            "MIDFIELDER" => pos is "CM" or "CAM" or "CDM" or "LM" or "RM" or "LAM" or "RAM" or "LCM" or "RCM" or "LDM" or "RDM",
            "DEFENDER" => pos is "CB" or "LB" or "RB" or "LWB" or "RWB" or "LCB" or "RCB",
            "GOALKEEPER" or "GK" => pos is "GK",
            _ => pos == req,
        };
    }
}