using System.ComponentModel;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server.Tools;

[McpServerToolType]
public sealed class PlayerTools
{
    private readonly PlayerService _playerService;

    public PlayerTools(SoccerDataContext context)
    {
        _playerService = new PlayerService(context);
    }

    [McpServerTool]
    [Description("Search for players by name, nationality, club, position, or minimum overall rating.")]
    public string SearchPlayers(
        [Description("Player name substring (optional)")] string? name = null,
        [Description("Nationality filter (optional)")] string? nationality = null,
        [Description("Club filter (optional)")] string? club = null,
        [Description("Position filter, e.g. ST, LW, GK (optional)")] string? position = null,
        [Description("Minimum overall rating (optional)")] int? minOverall = null,
        [Description("Maximum number of results to return (default 20)")] int? limit = 20)
    {
        var players = _playerService.SearchPlayers(name, nationality, club, position, minOverall, limit);
        var title = "Players";
        if (!string.IsNullOrWhiteSpace(name)) title += $" matching '{name}'";
        if (!string.IsNullOrWhiteSpace(nationality)) title += $" from {nationality}";
        if (!string.IsNullOrWhiteSpace(club)) title += $" at {club}";
        if (!string.IsNullOrWhiteSpace(position)) title += $" ({position})";
        return _playerService.FormatPlayers(players, title);
    }
}
