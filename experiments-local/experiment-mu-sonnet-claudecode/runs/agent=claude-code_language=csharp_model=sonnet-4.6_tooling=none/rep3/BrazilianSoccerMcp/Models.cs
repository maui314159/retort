namespace BrazilianSoccerMcp;

public record Match
{
    public DateTime Date { get; init; }
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    public int Season { get; init; }
    public string Competition { get; init; } = "";
    public string Round { get; init; } = "";
    public string Stage { get; init; } = "";
    public string? HomeState { get; init; }
    public string? AwayState { get; init; }
    public string? Arena { get; init; }
}

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
    public string? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public string? Value { get; init; }
    public string? Wage { get; init; }
    public int? Crossing { get; init; }
    public int? Finishing { get; init; }
    public int? Dribbling { get; init; }
    public int? Passing { get; init; }
    public int? Pace { get; init; }
    public int? Shooting { get; init; }
    public int? Defending { get; init; }
    public int? Physical { get; init; }
    public int? GkDiving { get; init; }
    public int? GkHandling { get; init; }
    public int? GkKicking { get; init; }
    public int? GkPositioning { get; init; }
    public int? GkReflexes { get; init; }
}

public record TeamStats
{
    public string Team { get; init; } = "";
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches > 0 ? (double)Wins / Matches * 100 : 0;
    public int GoalDiff => GoalsFor - GoalsAgainst;
}
