using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class PlayerTools(DataRepository repo)
{
    [McpServerTool(Name = "search_players")]
    [Description(
        "Search FIFA player database for Brazilian soccer players. Filter by name, " +
        "nationality, club, or position. Returns players sorted by overall rating.")]
    public string SearchPlayers(
        [Description("Player name (partial match). E.g. 'Neymar', 'Gabriel'")] string? name = null,
        [Description("Nationality. E.g. 'Brazil', 'Argentina'")] string? nationality = null,
        [Description("Club name (partial match). E.g. 'Flamengo', 'Palmeiras', 'Barcelona'")] string? club = null,
        [Description("Position. E.g. 'GK', 'CB', 'ST', 'LW', 'CAM'")] string? position = null,
        [Description("Minimum overall rating (0-99)")] int? minRating = null,
        [Description("Maximum results to return (default 20)")] int limit = 20)
    {
        var players = repo.SearchPlayers(name, nationality, club, position, minRating, limit);

        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s):");
        sb.AppendLine();

        int rank = 1;
        foreach (var p in players)
        {
            sb.AppendLine($"  {rank++,2}. {p.Name}");
            sb.AppendLine($"      Overall: {p.Overall} | Potential: {p.Potential} | Age: {p.Age}");
            sb.AppendLine($"      Club: {p.Club} | Position: {p.Position} | Nationality: {p.Nationality}");
            sb.AppendLine($"      Height: {p.Height} | Weight: {p.Weight} | Jersey: #{p.JerseyNumber}");
        }

        return sb.ToString();
    }

    [McpServerTool(Name = "get_players_at_club")]
    [Description(
        "Get all players at a specific club, grouped by position, sorted by rating. " +
        "Useful for understanding squad composition at Brazilian clubs.")]
    public string GetPlayersAtClub(
        [Description("Club name (partial match). E.g. 'Flamengo', 'Palmeiras'")] string club,
        [Description("Maximum results (default 30)")] int limit = 30)
    {
        var players = repo.SearchPlayers(club: club, limit: limit);

        if (players.Count == 0)
            return $"No players found at club '{club}'.";

        var sb = new StringBuilder();
        sb.AppendLine($"Players at {club} ({players.Count} found):");
        sb.AppendLine();

        var grouped = players
            .GroupBy(p => p.Position)
            .OrderBy(g => PositionOrder(g.Key));

        foreach (var group in grouped)
        {
            sb.AppendLine($"  [{group.Key}]");
            foreach (var p in group.OrderByDescending(p => p.Overall))
                sb.AppendLine($"    {p.Name} (OVR {p.Overall}, {p.Nationality})");
        }

        return sb.ToString();
    }

    private static int PositionOrder(string pos) => pos switch
    {
        "GK" => 1,
        "CB" or "LB" or "RB" or "LWB" or "RWB" => 2,
        "CDM" or "CM" or "LCM" or "RCM" => 3,
        "CAM" or "LM" or "RM" => 4,
        "LW" or "RW" or "LF" or "RF" or "CF" or "ST" => 5,
        _ => 6,
    };
}
