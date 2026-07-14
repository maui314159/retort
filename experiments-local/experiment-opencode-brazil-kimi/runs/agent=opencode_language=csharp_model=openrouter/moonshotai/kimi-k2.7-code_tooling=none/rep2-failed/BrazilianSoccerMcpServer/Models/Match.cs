namespace BrazilianSoccerMcpServer.Models;

public sealed record Match
{
    public int MatchId { get; init; }
    public DateTime? Date { get; init; }
    public string HomeTeam { get; init; } = string.Empty;
    public string AwayTeam { get; init; } = string.Empty;
    public string NormalizedHomeTeam { get; init; } = string.Empty;
    public string NormalizedAwayTeam { get; init; } = string.Empty;
    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }
    public string Competition { get; init; } = string.Empty;
    public int Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? HomeState { get; init; }
    public string? AwayState { get; init; }
    public string? Stadium { get; init; }
    public double? HomeCorners { get; init; }
    public double? AwayCorners { get; init; }
    public double? HomeShots { get; init; }
    public double? AwayShots { get; init; }
    public string? HalfTimeResult { get; init; }
    public string Source { get; init; } = string.Empty;

    public bool HasResult => HomeGoals.HasValue && AwayGoals.HasValue;

    public MatchOutcome HomeOutcome => HasResult
        ? HomeGoals!.Value > AwayGoals!.Value ? MatchOutcome.Win : HomeGoals!.Value < AwayGoals!.Value ? MatchOutcome.Loss : MatchOutcome.Draw
        : MatchOutcome.Unknown;

    public MatchOutcome AwayOutcome => HasResult
        ? HomeGoals!.Value < AwayGoals!.Value ? MatchOutcome.Win : HomeGoals!.Value > AwayGoals!.Value ? MatchOutcome.Loss : MatchOutcome.Draw
        : MatchOutcome.Unknown;

    public bool InvolvesTeam(string normalizedTeam)
    {
        return NormalizedHomeTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase)
            || NormalizedAwayTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase);
    }

    public bool IsBetween(string teamA, string teamB)
    {
        return InvolvesTeam(teamA) && InvolvesTeam(teamB);
    }

    public string FormatScore()
    {
        if (!HasResult)
            return "vs";
        return $"{HomeTeam} {HomeGoals}-{AwayGoals} {AwayTeam}";
    }

    public string WinnerName()
    {
        if (!HasResult)
            return "Unknown";
        if (HomeGoals!.Value > AwayGoals!.Value)
            return HomeTeam;
        if (HomeGoals!.Value < AwayGoals!.Value)
            return AwayTeam;
        return "Draw";
    }
}

public enum MatchOutcome
{
    Unknown,
    Win,
    Draw,
    Loss
}
