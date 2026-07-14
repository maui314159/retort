using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class PlayerTools(DataRepository repo)
{
    // ─── search_players ───────────────────────────────────────────────────────

    [McpServerTool(Name = "search_players")]
    [Description(
        "Search the FIFA player database (18 207 players). Filter by name, nationality, " +
        "club, position, or minimum overall rating.  Results are ordered by rating (highest first).")]
    public string SearchPlayers(
        [Description("Player name (partial match). E.g. 'Gabriel Barbosa', 'Neymar'.")]
        string? name = null,
        [Description("Player nationality. E.g. 'Brazil', 'Brazilian'.")]
        string? nationality = null,
        [Description("Club name (partial match). E.g. 'Flamengo', 'Palmeiras'.")]
        string? club = null,
        [Description("Playing position, e.g. 'GK', 'ST', 'CM'. Partial match.")]
        string? position = null,
        [Description("Minimum FIFA overall rating (1–99).")]
        int? minRating = null,
        [Description("Maximum results to return (default 20, max 100).")]
        int limit = 20)
    {
        limit = Math.Clamp(limit, 1, 100);

        var players = repo.FindPlayers(name, nationality, club, position, minRating)
                          .Take(limit)
                          .ToList();

        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s):");
        sb.AppendLine();

        int rank = 1;
        foreach (var p in players)
        {
            sb.AppendLine(
                $"{rank++,3}. {p.Name}  OVR:{p.Overall} POT:{p.Potential}  " +
                $"Pos:{p.Position}  Age:{p.Age}  Club:{p.Club}  Nationality:{p.Nationality}" +
                (p.JerseyNumber.HasValue ? $"  #{p.JerseyNumber}" : ""));
        }

        return sb.ToString().TrimEnd();
    }

    // ─── get_players_by_club ──────────────────────────────────────────────────

    [McpServerTool(Name = "get_players_by_club")]
    [Description(
        "Returns all players in the FIFA database for a given club, " +
        "sorted by overall rating. Includes aggregate statistics.")]
    public string GetPlayersByClub(
        [Description("Club name (partial match). E.g. 'Flamengo'.")]
        string club,
        [Description("Minimum overall rating filter (optional).")]
        int? minRating = null)
    {
        var players = repo.FindPlayers(club: club, minRating: minRating).ToList();

        if (players.Count == 0)
            return $"No players found at club matching '{club}'.";

        double avgRating = players.Average(p => p.Overall);
        var grouped = players.GroupBy(p => p.Position)
                             .OrderBy(g => g.Key)
                             .ToList();

        var sb = new StringBuilder();
        sb.AppendLine($"Players at {players[0].Club} ({players.Count} total, avg OVR: {avgRating:F1}):");
        sb.AppendLine();

        foreach (var g in grouped)
        {
            sb.AppendLine($"  {g.Key}:");
            foreach (var p in g.OrderByDescending(x => x.Overall))
                sb.AppendLine($"    - {p.Name}  OVR:{p.Overall}  {p.Nationality}" +
                              (p.JerseyNumber.HasValue ? $"  #{p.JerseyNumber}" : ""));
        }

        return sb.ToString().TrimEnd();
    }

    // ─── get_top_players ──────────────────────────────────────────────────────

    [McpServerTool(Name = "get_top_players")]
    [Description(
        "Returns the highest-rated players overall or for a specific nationality. " +
        "Great for finding top Brazilian players or comparing ratings.")]
    public string GetTopPlayers(
        [Description("Nationality filter, e.g. 'Brazil'. Leave empty for worldwide top.")]
        string? nationality = null,
        [Description("Position filter (optional).")]
        string? position = null,
        [Description("Number of players to return (default 20).")]
        int limit = 20)
    {
        limit = Math.Clamp(limit, 1, 100);

        var players = repo.FindPlayers(nationality: nationality, position: position)
                          .Take(limit)
                          .ToList();

        if (players.Count == 0)
            return "No players found.";

        var label = nationality != null ? $"{nationality} players" : "Top players";
        if (position != null) label += $" — {position}";

        var sb = new StringBuilder();
        sb.AppendLine($"{label} (FIFA ratings):");
        sb.AppendLine();

        int rank = 1;
        foreach (var p in players)
            sb.AppendLine(
                $"{rank++,3}. {p.Name,-28} OVR:{p.Overall}  POT:{p.Potential}  " +
                $"{p.Position,-4}  Club: {p.Club}  ({p.Nationality})");

        return sb.ToString().TrimEnd();
    }

    // ─── get_players_at_brazilian_clubs ──────────────────────────────────────

    [McpServerTool(Name = "get_brazilian_club_players")]
    [Description(
        "Returns a summary of players (by nationality) at the major Brazilian clubs " +
        "represented in the FIFA dataset.")]
    public string GetBrazilianClubPlayers(
        [Description("Nationality to focus on. Default is 'Brazil'.")]
        string nationality = "Brazil")
    {
        // Well-known Brazilian clubs that appear in the FIFA dataset
        var clubs = new[]
        {
            "Flamengo", "Palmeiras", "Corinthians", "Santos", "São Paulo",
            "Grêmio", "Internacional", "Fluminense", "Atletico Mineiro",
            "Cruzeiro", "Botafogo", "Vasco", "Athletico-PR", "Fortaleza",
        };

        var sb = new StringBuilder();
        sb.AppendLine($"{nationality} players at major Brazilian clubs:");
        sb.AppendLine();

        foreach (var clubName in clubs)
        {
            var players = repo.FindPlayers(nationality: nationality, club: clubName).ToList();
            if (players.Count == 0) continue;

            double avg = players.Average(p => p.Overall);
            var top3   = players.Take(3).Select(p => $"{p.Name} ({p.Overall})");
            sb.AppendLine($"  {clubName,-22} {players.Count,2} players  avg:{avg:F0}  " +
                          $"Top: {string.Join(", ", top3)}");
        }

        return sb.ToString().TrimEnd();
    }
}
