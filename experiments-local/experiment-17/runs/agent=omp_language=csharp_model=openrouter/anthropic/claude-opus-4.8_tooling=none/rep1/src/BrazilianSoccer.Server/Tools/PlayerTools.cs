// -----------------------------------------------------------------------------
// File: Tools/PlayerTools.cs
// Project: BrazilianSoccer.Server
//
// Context:
//   MCP tools for "Player Queries" over the FIFA dataset: search by name,
//   nationality, club, position, and minimum Overall rating, plus a club
//   breakdown that groups matching players by club with average ratings. Backs
//   "Who is Gabriel Barbosa?", "Find all Brazilian players", "highest-rated
//   players at Flamengo", and "Brazilian players at Brazilian clubs". Output uses
//   the numbered/grouped formats from the spec.
// -----------------------------------------------------------------------------

using System.ComponentModel;
using BrazilianSoccer.Core.Queries;
using ModelContextProtocol.Server;

namespace BrazilianSoccer.Server.Tools;

/// <summary>MCP tools for searching the FIFA player database.</summary>
[McpServerToolType]
public sealed class PlayerTools
{
    [McpServerTool(Name = "find_players")]
    [Description("Search FIFA players by any combination of name, nationality, club, position, and minimum " +
                 "Overall rating. Results are ranked by Overall rating (highest first). Use nationality " +
                 "'Brazil' for Brazilian players.")]
    public static string FindPlayers(
        PlayerQueryService players,
        [Description("Player name substring, e.g. 'Neymar'.")] string? name = null,
        [Description("Nationality, e.g. 'Brazil'.")] string? nationality = null,
        [Description("Club name, e.g. 'Flamengo' (accent/case insensitive).")] string? club = null,
        [Description("Playing position, e.g. 'ST', 'GK', 'LW'.")] string? position = null,
        [Description("Minimum FIFA Overall rating, e.g. 80.")] int? minOverall = null,
        [Description("Maximum number of players to list (default 20).")] int limit = 20)
    {
        if (string.IsNullOrWhiteSpace(name) && string.IsNullOrWhiteSpace(nationality)
            && string.IsNullOrWhiteSpace(club) && string.IsNullOrWhiteSpace(position)
            && minOverall is null)
        {
            return "Provide at least one filter: name, nationality, club, position, or minOverall.";
        }

        var results = players.Find(name, nationality, club, position, minOverall, limit: null);
        var header = BuildHeader(name, nationality, club, position, minOverall, results.Count);
        return ResponseFormatter.PlayerList(header, results, show: limit);
    }

    [McpServerTool(Name = "players_by_club")]
    [Description("Group matching players by club, showing player count and average Overall rating per club " +
                 "(highest count first). Useful for 'Brazilian players at Brazilian clubs'.")]
    public static string PlayersByClub(
        PlayerQueryService players,
        [Description("Nationality filter, e.g. 'Brazil'.")] string? nationality = null,
        [Description("Club name filter (partial match).")] string? club = null,
        [Description("Position filter, e.g. 'ST'.")] string? position = null,
        [Description("Minimum Overall rating.")] int? minOverall = null,
        [Description("Maximum number of clubs to list (default 15).")] int limit = 15)
    {
        var clubs = players.ClubBreakdown(nationality, club, position, minOverall, maxClubs: null);
        var header = "Players by club" + ScopeSuffix(nationality, position, minOverall) + ":";
        return ResponseFormatter.ClubBreakdown(header, clubs, show: limit);
    }

    private static string BuildHeader(
        string? name, string? nationality, string? club, string? position, int? minOverall, int count)
    {
        var filters = new List<string>();
        if (!string.IsNullOrWhiteSpace(name)) filters.Add($"name~'{name}'");
        if (!string.IsNullOrWhiteSpace(nationality)) filters.Add(nationality!);
        if (!string.IsNullOrWhiteSpace(club)) filters.Add($"club~'{club}'");
        if (!string.IsNullOrWhiteSpace(position)) filters.Add($"position {position}");
        if (minOverall is not null) filters.Add($"Overall>={minOverall}");

        var scope = filters.Count == 0 ? "" : " (" + string.Join(", ", filters) + ")";
        return $"Players{scope} — {count} found:";
    }

    private static string ScopeSuffix(string? nationality, string? position, int? minOverall)
    {
        var filters = new List<string>();
        if (!string.IsNullOrWhiteSpace(nationality)) filters.Add(nationality!);
        if (!string.IsNullOrWhiteSpace(position)) filters.Add($"position {position}");
        if (minOverall is not null) filters.Add($"Overall>={minOverall}");
        return filters.Count == 0 ? "" : " (" + string.Join(", ", filters) + ")";
    }
}
