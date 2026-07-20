using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class PlayerTools
{
    private readonly DataService _data;

    public PlayerTools(DataService data) => _data = data;

    [McpServerTool]
    [Description("Search for soccer players by name, nationality, club, or position. Uses FIFA player database.")]
    public string SearchPlayers(
        [Description("Player name to search (partial match supported, e.g. 'Neymar', 'Gabriel').")] string? name = null,
        [Description("Nationality filter (e.g. 'Brazilian', 'Argentina').")] string? nationality = null,
        [Description("Club filter (e.g. 'Flamengo', 'Palmeiras', 'Santos').")] string? club = null,
        [Description("Position filter (e.g. 'ST', 'GK', 'CM', 'LW').")] string? position = null,
        [Description("Minimum overall FIFA rating (0-99).")] int? minOverall = null,
        [Description("Maximum age filter.")] int? maxAge = null,
        [Description("Maximum results to return (default 20, max 50).")] int limit = 20)
    {
        limit = Math.Clamp(limit, 1, 50);

        var players = _data.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
            players = players.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(nationality))
            players = players.Where(p => NationalityMatches(p.Nationality, nationality));

        if (!string.IsNullOrWhiteSpace(club))
            players = players.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            players = players.Where(p => p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));

        if (minOverall.HasValue)
            players = players.Where(p => p.Overall >= minOverall);

        if (maxAge.HasValue)
            players = players.Where(p => p.Age <= maxAge);

        var results = players.OrderByDescending(p => p.Overall).Take(limit).ToList();

        if (results.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} player(s):");
        sb.AppendLine();

        for (int i = 0; i < results.Count; i++)
        {
            var p = results[i];
            sb.AppendLine($"{i + 1}. {p.Name}");
            sb.AppendLine($"   Overall: {p.Overall} | Potential: {p.Potential} | Age: {p.Age}");
            sb.AppendLine($"   Nationality: {p.Nationality} | Club: {p.Club} | Position: {p.Position}");
            if (p.Height != null || p.Weight != null)
                sb.AppendLine($"   Height: {p.Height} | Weight: {p.Weight}");
        }

        return sb.ToString();
    }

    [McpServerTool]
    [Description("Get top-rated players filtered by nationality, club, or position.")]
    public string GetTopPlayers(
        [Description("Nationality filter (e.g. 'Brazilian').")] string? nationality = null,
        [Description("Club filter (e.g. 'Flamengo').")] string? club = null,
        [Description("Position filter (e.g. 'ST', 'GK').")] string? position = null,
        [Description("Number of top players to return (default 10, max 50).")] int limit = 10)
    {
        limit = Math.Clamp(limit, 1, 50);

        var players = _data.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(nationality))
            players = players.Where(p => NationalityMatches(p.Nationality, nationality));

        if (!string.IsNullOrWhiteSpace(club))
            players = players.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            players = players.Where(p => p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));

        var results = players.OrderByDescending(p => p.Overall).Take(limit).ToList();

        if (results.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();

        var filterDesc = string.Join(", ", new[]
        {
            nationality != null ? $"Nationality: {nationality}" : null,
            club != null ? $"Club: {club}" : null,
            position != null ? $"Position: {position}" : null,
        }.Where(x => x != null));

        sb.AppendLine($"Top {results.Count} players{(filterDesc.Length > 0 ? $" ({filterDesc})" : "")}:");
        sb.AppendLine();

        for (int i = 0; i < results.Count; i++)
        {
            var p = results[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall} | Position: {p.Position} | Club: {p.Club} | Nationality: {p.Nationality} | Age: {p.Age}");
        }

        return sb.ToString();
    }

    private static bool NationalityMatches(string dbNationality, string searchTerm)
    {
        if (string.IsNullOrWhiteSpace(dbNationality) || string.IsNullOrWhiteSpace(searchTerm))
            return false;
        // Bidirectional contains: "Brazil".Contains("Brazil") AND "Brazilian".Contains("Brazil")
        return dbNationality.Contains(searchTerm, StringComparison.OrdinalIgnoreCase)
            || searchTerm.Contains(dbNationality, StringComparison.OrdinalIgnoreCase);
    }

    [McpServerTool]
    [Description("Get summary of players grouped by club for Brazilian clubs. Shows how many players per club and their average rating.")]
    public string GetBrazilianClubPlayers(
        [Description("Nationality to filter by (default 'Brazilian').")] string nationality = "Brazilian")
    {
        var players = _data.Players
            .Where(p => NationalityMatches(p.Nationality, nationality))
            .ToList();

        if (players.Count == 0)
            return $"No players found with nationality '{nationality}'.";

        var byClub = players
            .GroupBy(p => p.Club)
            .Select(g => new
            {
                Club = g.Key,
                Count = g.Count(),
                AvgOverall = g.Average(p => p.Overall ?? 0),
                TopPlayer = g.OrderByDescending(p => p.Overall).First()
            })
            .OrderByDescending(g => g.AvgOverall)
            .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"{nationality} players by club (top 30 clubs by average rating):");
        sb.AppendLine();

        foreach (var c in byClub.Take(30))
        {
            sb.AppendLine($"- {c.Club}: {c.Count} player(s), avg rating {c.AvgOverall:F0} | Best: {c.TopPlayer.Name} ({c.TopPlayer.Overall})");
        }

        sb.AppendLine();
        sb.AppendLine($"Total {nationality} players: {players.Count} across {byClub.Count} clubs");

        return sb.ToString();
    }
}
