using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>
/// MCP tools for searching FIFA player data.
/// </summary>
[McpServerToolType]
public static class PlayerTools
{
    private static DataLoader Data => DataStore.Loader;

    [McpServerTool, Description("Search players by name, nationality, club, or position. Returns player details including FIFA ratings and attributes.")]
    public static string SearchPlayers(
        [Description("Player name to search for (partial match). Example: 'Neymar', 'Gabriel'.")] string? name = null,
        [Description("Nationality filter, e.g. 'Brazil', 'Argentina'.")] string? nationality = null,
        [Description("Club name filter, e.g. 'Flamengo', 'São Paulo'.")] string? club = null,
        [Description("Playing position, e.g. 'LW', 'GK', 'ST', 'CDM'.")] string? position = null,
        [Description("Sort by: 'overall' (default), 'potential', 'name'.")] string sortBy = "overall",
        [Description("Maximum results (default 20).")] int limit = 20)
    {
        var query = Data.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(nationality))
            query = query.Where(p => p.Nationality.Equals(nationality, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(club))
            query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p => p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));

        query = sortBy.ToLowerInvariant() switch
        {
            "potential" => query.OrderByDescending(p => p.Potential),
            "name" => query.OrderBy(p => p.Name),
            _ => query.OrderByDescending(p => p.Overall),
        };

        var players = query.Take(limit).ToList();

        if (players.Count == 0)
        {
            var filters = new List<string>();
            if (!string.IsNullOrWhiteSpace(name)) filters.Add($"name '{name}'");
            if (!string.IsNullOrWhiteSpace(nationality)) filters.Add($"nationality '{nationality}'");
            if (!string.IsNullOrWhiteSpace(club)) filters.Add($"club '{club}'");
            if (!string.IsNullOrWhiteSpace(position)) filters.Add($"position '{position}'");
            return $"No players found matching: {string.Join(", ", filters)}.";
        }

        var sb = new StringBuilder();
        sb.AppendLine($"Players ({players.Count} shown):");
        sb.AppendLine();

        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"  {i + 1}. {p.Name}");
            sb.AppendLine($"     Overall: {p.Overall}, Potential: {p.Potential}, Age: {p.Age}");
            sb.AppendLine($"     Position: {p.Position}, Nationality: {p.Nationality}, Club: {p.Club}");
            if (!string.IsNullOrWhiteSpace(p.PreferredFoot))
                sb.AppendLine($"     Foot: {p.PreferredFoot}, Height: {p.Height}, Weight: {p.Weight}");
            if (p.Crossing > 0 || p.Finishing > 0 || p.Dribbling > 0 || p.Passing > 0)
                sb.AppendLine($"     Skills: CRO:{p.Crossing} FIN:{p.Finishing} DRI:{p.Dribbling} PAS:{p.Passing}");
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Get the top-rated players from a specific club, sorted by overall rating.")]
    public static string GetTopPlayersByClub(
        [Description("Club name, e.g. 'Flamengo', 'São Paulo', 'Palmeiras'.")] string club,
        [Description("Number of players to return (default 10).")] int limit = 10)
    {
        var players = Data.Players
            .Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();

        if (players.Count == 0)
            return $"No players found for club '{club}'.";

        var avgOverall = players.Average(p => p.Overall);
        var avgPotential = players.Average(p => p.Potential);

        var sb = new StringBuilder();
        sb.AppendLine($"Top {players.Count} players at {club}:");
        sb.AppendLine($"  (Average Overall: {avgOverall:F1}, Average Potential: {avgPotential:F1})");
        sb.AppendLine();

        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"  {i + 1}. {p.Name} - Overall: {p.Overall}, Pot: {p.Potential}, Pos: {p.Position}, Age: {p.Age}");
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool, Description("Find Brazilian players in the dataset, optionally filtered by club or position.")]
    public static string FindBrazilianPlayers(
        [Description("Optional club filter.")] string? club = null,
        [Description("Optional position filter.")] string? position = null,
        [Description("Sort by: 'overall' (default), 'potential'.")] string sortBy = "overall",
        [Description("Maximum results (default 25).")] int limit = 25)
    {
        var query = Data.Players.Where(p => p.Nationality == "Brazil");

        if (!string.IsNullOrWhiteSpace(club))
            query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(p => p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));

        query = sortBy.ToLowerInvariant() == "potential"
            ? query.OrderByDescending(p => p.Potential)
            : query.OrderByDescending(p => p.Overall);

        var players = query.Take(limit).ToList();

        var totalCount = Data.Players.Count(p => p.Nationality == "Brazil");

        var sb = new StringBuilder();
        sb.AppendLine($"Brazilian players found: {players.Count} shown (of {totalCount} total in dataset)");
        sb.AppendLine();

        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"  {i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}");
        }

        return sb.ToString().TrimEnd();
    }
}