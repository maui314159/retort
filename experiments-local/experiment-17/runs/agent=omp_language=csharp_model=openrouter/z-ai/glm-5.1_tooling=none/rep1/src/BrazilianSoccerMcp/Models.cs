namespace BrazilianSoccerMcp;

/// <summary>Unified match record used across all data sources.</summary>
public record Match
{
    public string Competition { get; init; } = "";
    public DateOnly Date { get; init; }
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    public int Season { get; init; }
    public string Round { get; init; } = "";
    public string Stage { get; init; } = "";
    public string? HomeState { get; init; }
    public string? AwayState { get; init; }
    public string? Stadium { get; init; }
}

/// <summary>Player record from FIFA data.</summary>
public record Player
{
    public int Id { get; init; }
    public string Name { get; init; } = "";
    public int Age { get; init; }
    public string Nationality { get; init; } = "";
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = "";
    public string Position { get; init; } = "";
    public int JerseyNumber { get; init; }
}

/// <summary>Team statistics computed from match data.</summary>
public record TeamStats
{
    public string Team { get; init; } = "";
    public string Competition { get; init; } = "";
    public int? Season { get; init; }
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int HomeWins { get; init; }
    public int HomeDraws { get; init; }
    public int HomeLosses { get; init; }
    public int AwayWins { get; init; }
    public int AwayDraws { get; init; }
    public int AwayLosses { get; init; }
    public double WinRate => Matches > 0 ? Math.Round((double)Wins / Matches * 100, 1) : 0;
    public int Points => Wins * 3 + Draws;
}

/// <summary>Head-to-head record between two teams.</summary>
public record HeadToHead
{
    public string Team1 { get; init; } = "";
    public string Team2 { get; init; } = "";
    public int TotalMatches { get; init; }
    public int Team1Wins { get; init; }
    public int Team2Wins { get; init; }
    public int Draws { get; init; }
    public List<Match> Matches { get; init; } = [];
}

/// <summary>Competition standings entry.</summary>
public record StandingEntry
{
    public int Position { get; init; }
    public string Team { get; init; } = "";
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public int Points => Wins * 3 + Draws;
}
