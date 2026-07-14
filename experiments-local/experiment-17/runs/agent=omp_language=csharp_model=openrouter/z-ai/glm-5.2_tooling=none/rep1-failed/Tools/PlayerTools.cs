// ============================================================================
// File: Tools/PlayerTools.cs
// ----------------------------------------------------------------------------
// Context: MCP tools for the "Player Queries" category: search the FIFA player
// database by name / nationality / club / position / minimum rating, and
// "top players" ranking. Brazilian clubs and nationalities are the typical
// filter (e.g. "Brazilian players", "players at Flamengo").
// ============================================================================

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class PlayerTools
{
    private readonly SoccerDataStore _store;
    public PlayerTools(SoccerDataStore store) => _store = store;

    /// <summary>Search the FIFA player database.</summary>
    [McpServerTool, Description(
        "Search FIFA player data by name, nationality (e.g. Brazil), club " +
        "(e.g. Flamengo), position (e.g. ST, LW, GK), and/or minimum overall " +
        "rating. Returns name, overall, position, club, age, nationality.")]
    public string SearchPlayers(
        [Description("Name fragment (optional).")] string? name = null,
        [Description("Nationality, e.g. Brazil (optional).")] string? nationality = null,
        [Description("Club name fragment, e.g. Flamengo (optional).")] string? club = null,
        [Description("Position code, e.g. ST, LW, CAM, GK (optional).")] string? position = null,
        [Description("Minimum overall rating (optional).")] int? minRating = null,
        [Description("Max players to return (default 25).")] int limit = 25)
    {
        if (limit <= 0) limit = 25;

        var players = _store.SearchPlayers(name, nationality, club, position, minRating)
            .OrderByDescending(p => p.Overall)
            .ThenBy(p => p.Name, StringComparer.OrdinalIgnoreCase)
            .Take(limit)
            .ToList();

        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s) (sorted by overall rating):");
        foreach (var p in players)
        {
            sb.AppendLine(CultureInfo.InvariantCulture,
                $"- {p.Name} | Overall {p.Overall} | Pos {p.Position} | {p.Club} | Age {p.Age} | {p.Nationality}");
        }
        return sb.ToString().TrimEnd();
    }

    /// <summary>Top-rated players by filter.</summary>
    [McpServerTool, Description(
        "Rank the highest-rated players, optionally filtered by nationality, " +
        "club or position. Useful for 'top Brazilian players', 'best players at Flamengo'.")]
    public string TopPlayers(
        [Description("Nationality filter (optional).")] string? nationality = null,
        [Description("Club filter (optional).")] string? club = null,
        [Description("Position filter (optional).")] string? position = null,
        [Description("How many players to list (default 10).")] int limit = 10)
    {
        if (limit <= 0) limit = 10;
        return SearchPlayers(name: null, nationality, club, position, minRating: null, limit: limit);
    }

    /// <summary>Count of Brazilian players grouped by Brazilian club.</summary>
    [McpServerTool, Description(
        "Show Brazilian players grouped by Brazilian club (average rating and count). " +
        "Answers 'which Brazilian clubs have Brazilian players'.")]
    public string BrazilianPlayersAtBrazilianClubs([Description("Max clubs (default 15).")] int limit = 15)
    {
        if (limit <= 0) limit = 15;

        // Known Brazilian clubs present (by name fragment) in the FIFA dataset.
        var brazilianClubs = new[]
        {
            "Flamengo", "Palmeiras", "São Paulo", "Santos", "Corinthians", "Grêmio",
            "Internacional", "Atlético-MG", "Athletico-PR", "Cruzeiro", "Botafogo",
            "Fluminense", "Bahia", "Vasco", "Fortaleza", "Ceará", "Sport", "Coritiba",
            "Goiás", "Cuiabá", "Athletico", "Bragantino"
        };

        var groups = new List<(string Club, int Count, double Avg)>();
        foreach (var club in brazilianClubs)
        {
            var players = _store.SearchPlayers(nationality: "Brazil", club: club).ToList();
            if (players.Count == 0) continue;
            groups.Add((club, players.Count, players.Average(p => p.Overall)));
        }

        if (groups.Count == 0)
            return "No Brazilian players at Brazilian clubs found in the dataset.";

        var sb = new StringBuilder();
        sb.AppendLine("Brazilian players at Brazilian clubs in dataset:");
        foreach (var g in groups.OrderByDescending(g => g.Count).Take(limit))
            sb.AppendLine($"- {g.Club}: {g.Count} players (avg rating: {g.Avg:0})");
        return sb.ToString().TrimEnd();
    }
}
