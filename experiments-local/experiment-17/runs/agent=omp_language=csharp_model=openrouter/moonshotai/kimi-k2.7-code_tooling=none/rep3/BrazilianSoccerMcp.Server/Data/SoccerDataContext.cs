using BrazilianSoccerMcp.Server.Models;

namespace BrazilianSoccerMcp.Server.Data;

public sealed class SoccerDataContext
{
    public IReadOnlyList<MatchRecord> Matches { get; }
    public IReadOnlyList<PlayerRecord> Players { get; }

    public SoccerDataContext(IEnumerable<MatchRecord> matches, IEnumerable<PlayerRecord> players)
    {
        Matches = matches.ToList().AsReadOnly();
        Players = players.ToList().AsReadOnly();
    }
}
