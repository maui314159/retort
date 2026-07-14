using System.Text;
using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Models;

namespace BrazilianSoccerMcp.Server.Services;

public sealed class PlayerService
{
    private readonly SoccerDataContext _context;

    public PlayerService(SoccerDataContext context)
    {
        _context = context;
    }

    public IReadOnlyList<PlayerRecord> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? limit = null)
    {
        var query = _context.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            query = query.Where(p =>
                p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            query = query.Where(p =>
                p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            query = query.Where(p =>
                p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            query = query.Where(p =>
                p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }

        if (minOverall.HasValue)
        {
            query = query.Where(p => p.Overall >= minOverall.Value);
        }

        query = query.OrderByDescending(p => p.Overall ?? 0);

        if (limit.HasValue)
        {
            query = query.Take(limit.Value);
        }

        return query.ToList();
    }

    public string FormatPlayers(IEnumerable<PlayerRecord> players, string title)
    {
        var list = players.ToList();
        var sb = new StringBuilder();
        sb.AppendLine(title);

        if (list.Count == 0)
        {
            sb.AppendLine("No players found.");
            return sb.ToString();
        }

        for (int i = 0; i < list.Count; i++)
        {
            var p = list[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}");
        }

        return sb.ToString();
    }
}
