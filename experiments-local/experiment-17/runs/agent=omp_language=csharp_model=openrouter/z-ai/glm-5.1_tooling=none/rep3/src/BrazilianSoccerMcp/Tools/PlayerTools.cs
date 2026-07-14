using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class PlayerTools
{
    private readonly PlayerDataLoader _playerLoader;

    public PlayerTools(PlayerDataLoader playerLoader) => _playerLoader = playerLoader;

    [McpServerTool, Description(
        "Search for soccer players by name, nationality, club, position, or minimum overall rating. " +
        "Returns player information including ratings, position, and club.")]
    public string search_players(
        [Description("Player name to search for (partial match). Optional.")]
        string? name = null,
        [Description("Nationality filter. e.g. 'Brazil', 'Argentina'")]
        string? nationality = null,
        [Description("Club name filter. e.g. 'Flamengo', 'Palmeiras'")]
        string? club = null,
        [Description("Position filter. e.g. 'ST', 'GK', 'CM', 'LW', 'CB'")]
        string? position = null,
        [Description("Minimum overall rating. e.g. 80")]
        int? min_overall = null,
        [Description("Maximum number of results to return. Default 20.")]
        int limit = 20)
    {
        var players = _playerLoader.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            players = players.Where(p =>
                p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            players = players.Where(p =>
                p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            players = players.Where(p =>
                TeamNameNormalizer.Matches(p.Club, club));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            players = players.Where(p =>
                p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));
        }

        if (min_overall.HasValue)
        {
            players = players.Where(p => p.Overall >= min_overall.Value);
        }

        var results = players.OrderByDescending(p => p.Overall).Take(limit).ToList();

        if (results.Count == 0)
            return "No players found matching the specified criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {results.Count} player(s):");
        sb.AppendLine();

        for (int i = 0; i < results.Count; i++)
        {
            var p = results[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}, Age: {p.Age}, Nationality: {p.Nationality}");
        }

        // If filtering by nationality and club not specified, show club summary
        if (!string.IsNullOrWhiteSpace(nationality) && string.IsNullOrWhiteSpace(club))
        {
            var allNationality = _playerLoader.Players
                .Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase))
                .ToList();

            var brazilianClubs = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "Flamengo", "Palmeiras", "São Paulo", "Santos", "Corinthians",
                "Grêmio", "Internacional", "Fluminense", "Botafogo", "Vasco",
                "Cruzeiro", "Atlético-MG", "Bahia", "Fortaleza", "Athletico-PR",
                "Bragantino", "Cuiabá", "Goiás", "América-MG", "Coritiba"
            };

            var clubGroups = allNationality
                .Where(p => brazilianClubs.Any(bc => TeamNameNormalizer.Matches(p.Club, bc)))
                .GroupBy(p => p.Club)
                .OrderByDescending(g => g.Count())
                .Take(10)
                .ToList();

            if (clubGroups.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine($"{nationality} players at Brazilian clubs:");
                foreach (var g in clubGroups)
                {
                    var avgRating = Math.Round(g.Average(p => p.Overall), 1);
                    sb.AppendLine($"  {g.Key}: {g.Count()} players (avg rating: {avgRating})");
                }
            }
        }

        return sb.ToString();
    }
}
