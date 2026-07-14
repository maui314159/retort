namespace BrazilianSoccerMcpServer.Models;

public sealed record HeadToHead
{
    public string TeamA { get; init; } = string.Empty;
    public string TeamB { get; init; } = string.Empty;
    public int Matches { get; init; }
    public int WinsA { get; init; }
    public int WinsB { get; init; }
    public int Draws { get; init; }
    public int GoalsA { get; init; }
    public int GoalsB { get; init; }
    public List<Match> MatchesList { get; init; } = new();
}
