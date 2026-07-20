using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public class PlayerTools(SoccerDataService dataService)
{
    [McpServerTool(Name = "find_players"), Description(
        "Search for players in the FIFA dataset. Filter by name, nationality, club, position, or minimum rating. " +
        "Returns player name, nationality, club, position, overall rating, and potential.")]
    public string FindPlayers(
        [Description("Player name or partial name (e.g., 'Neymar', 'Gabriel')")]
        string? name = null,
        [Description("Nationality (e.g., 'Brazilian', 'Argentine')")]
        string? nationality = null,
        [Description("Club name (e.g., 'Flamengo', 'Palmeiras', 'Paris Saint-Germain')")]
        string? club = null,
        [Description("Position (e.g., 'GK', 'CB', 'ST', 'LW', 'CAM')")]
        string? position = null,
        [Description("Minimum overall rating (0-99)")]
        int? minRating = null,
        [Description("Maximum results to return (default 20, max 100)")]
        int limit = 20)
    {
        limit = Math.Clamp(limit, 1, 100);

        if (name == null && nationality == null && club == null && position == null && minRating == null)
            return "Please provide at least one search filter: name, nationality, club, position, or minRating.";

        var players = dataService.FindPlayers(name, nationality, club, position, minRating, limit);

        if (players.Count == 0)
            return $"No players found matching the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s):");
        sb.AppendLine();

        foreach (var p in players)
        {
            var jersey = p.JerseyNumber.HasValue ? $" #{p.JerseyNumber}" : "";
            sb.AppendLine($"  {p.Name}{jersey}");
            sb.AppendLine($"    Club: {p.Club} | Position: {p.Position} | Nationality: {p.Nationality}");
            sb.AppendLine($"    Overall: {p.Overall} | Potential: {p.Potential} | Age: {p.Age}");
        }

        return sb.ToString().TrimEnd();
    }

    [McpServerTool(Name = "get_top_players_at_club"), Description(
        "Get the highest-rated players at a specific club from the FIFA dataset.")]
    public string GetTopPlayersAtClub(
        [Description("Club name (e.g., 'Flamengo', 'Corinthians')")]
        string club,
        [Description("Number of top players to return (default 10)")]
        int count = 10)
    {
        count = Math.Clamp(count, 1, 50);
        var players = dataService.FindPlayers(club: club, limit: count);

        if (players.Count == 0)
            return $"No players found for club '{club}'.";

        var sb = new StringBuilder();
        sb.AppendLine($"Top {players.Count} rated player(s) at {club}:");
        sb.AppendLine();
        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"  {i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Age: {p.Age}, Nationality: {p.Nationality}");
        }
        return sb.ToString().TrimEnd();
    }
}
