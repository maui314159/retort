using System.ComponentModel;
using System.Text;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

/// <summary>MCP tools answering questions about players (category 3 of the spec).</summary>
[McpServerToolType]
public sealed class PlayerTools
{
    private readonly SoccerDataService _data;
    public PlayerTools(SoccerDataService data) => _data = data;

    [McpServerTool(Name = "search_players"),
     Description("Search FIFA player data by name, nationality, club, position and/or minimum " +
                 "overall rating. Examples: 'Find all Brazilian players' -> nationality='Brazil'; " +
                 "'highest-rated players at Flamengo' -> club='Flamengo'; " +
                 "'forwards from São Paulo FC' -> club='São Paulo', position='ST'. " +
                 "Results are sorted by overall rating (best first).")]
    public string SearchPlayers(
        [Description("Player name substring (optional)")] string? name = null,
        [Description("Nationality, e.g. 'Brazil' (optional)")] string? nationality = null,
        [Description("Club name substring (optional)")] string? club = null,
        [Description("Position code, e.g. 'ST', 'LW', 'GK', 'CDM' (optional)")] string? position = null,
        [Description("Minimum overall rating 1-99 (optional)")] int? min_overall = null,
        [Description("Max players to return (default 15)")] int limit = 15)
    {
        var players = _data.SearchPlayers(name, nationality, club, position, min_overall, limit);
        if (players.Count == 0) return "No players found for the given criteria.";

        var titleBits = new List<string>();
        if (!string.IsNullOrWhiteSpace(nationality)) titleBits.Add(nationality);
        titleBits.Add("players");
        if (!string.IsNullOrWhiteSpace(club)) titleBits.Add($"at {club}");
        if (!string.IsNullOrWhiteSpace(position)) titleBits.Add($"({position})");
        if (!string.IsNullOrWhiteSpace(name)) titleBits.Add($"matching '{name}'");

        var sb = new StringBuilder($"Top {string.Join(' ', titleBits)} in dataset:\n");
        var i = 1;
        foreach (var p in players)
        {
            sb.AppendLine($"{i}. {p.Name} - Overall: {p.Overall?.ToString() ?? "?"}, " +
                          $"Position: {p.Position ?? "?"}, Club: {p.Club ?? "?"}, " +
                          $"Age: {p.Age?.ToString() ?? "?"}, Nationality: {p.Nationality ?? "?"}");
            i++;
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_player"),
     Description("Get detailed information about a single player by name " +
                 "(e.g. 'Gabriel Barbosa', 'Neymar'). Returns ratings, position, club " +
                 "and physical attributes from the FIFA dataset.")]
    public string GetPlayer(
        [Description("Player name (full or partial)")] string name)
    {
        var players = _data.SearchPlayers(name: name, limit: 3);
        if (players.Count == 0) return $"No player named '{name}' found in the FIFA dataset.";

        var p = players[0];
        var sb = new StringBuilder($"{p.Name}:\n");
        sb.AppendLine($"- Nationality: {p.Nationality ?? "?"}");
        sb.AppendLine($"- Age: {p.Age?.ToString() ?? "?"}");
        sb.AppendLine($"- Club: {p.Club ?? "?"}");
        sb.AppendLine($"- Position: {p.Position ?? "?"}, Jersey: {p.JerseyNumber?.ToString() ?? "?"}");
        sb.AppendLine($"- Overall: {p.Overall?.ToString() ?? "?"}, Potential: {p.Potential?.ToString() ?? "?"}");
        sb.AppendLine($"- Preferred foot: {p.PreferredFoot ?? "?"}");
        sb.AppendLine($"- Height: {p.Height ?? "?"}, Weight: {p.Weight ?? "?"}");
        if (p.Crossing is not null || p.Finishing is not null || p.Dribbling is not null)
            sb.AppendLine($"- Skills: Crossing {p.Crossing?.ToString() ?? "?"}, " +
                          $"Finishing {p.Finishing?.ToString() ?? "?"}, " +
                          $"Dribbling {p.Dribbling?.ToString() ?? "?"}, " +
                          $"Short passing {p.ShortPassing?.ToString() ?? "?"}, " +
                          $"Sprint speed {p.SprintSpeed?.ToString() ?? "?"}");
        if (players.Count > 1)
        {
            sb.AppendLine();
            sb.AppendLine("Other players with similar names: " +
                          string.Join(", ", players.Skip(1).Select(x => $"{x.Name} ({x.Club ?? "?"})")));
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "get_club_player_summary"),
     Description("Summarize players per club (count and average overall rating), optionally " +
                 "filtered by nationality. Example: 'Brazilian players at Brazilian clubs' -> " +
                 "nationality='Brazil'.")]
    public string GetClubPlayerSummary(
        [Description("Nationality filter, e.g. 'Brazil' (optional)")] string? nationality = null,
        [Description("Max clubs to return (default 15)")] int limit = 15)
    {
        var rows = _data.GetClubPlayerSummary(nationality, limit);
        if (rows.Count == 0) return "No player data for the given filter.";

        var title = string.IsNullOrWhiteSpace(nationality)
            ? "Players per club in FIFA dataset:\n"
            : $"{nationality} players per club in FIFA dataset:\n";
        var sb = new StringBuilder(title);
        foreach (var (club, count, avg) in rows)
            sb.AppendLine($"- {club}: {count} players (avg rating: {avg:F1})");
        return sb.ToString();
    }
}
