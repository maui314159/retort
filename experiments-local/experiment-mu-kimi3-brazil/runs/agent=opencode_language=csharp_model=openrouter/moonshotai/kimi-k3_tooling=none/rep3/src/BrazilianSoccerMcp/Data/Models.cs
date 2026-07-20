namespace BrazilianSoccerMcp.Data;

/// <summary>A unified match record built from any of the five match CSV sources.</summary>
public sealed record Match
{
    public required string Id { get; init; }
    public DateTime? Date { get; init; }
    public int? Season { get; init; }

    /// <summary>Canonical competition name, e.g. "Brasileirão Série A", "Copa do Brasil", "Copa Libertadores".</summary>
    public required string Competition { get; init; }

    /// <summary>Round number or cup stage, as text (e.g. "22", "final").</summary>
    public string? Round { get; init; }

    /// <summary>Home team name exactly as written in the source file.</summary>
    public required string HomeTeam { get; init; }

    /// <summary>Away team name exactly as written in the source file.</summary>
    public required string AwayTeam { get; init; }

    /// <summary>Normalized canonical key for the home team (see <see cref="TeamNameNormalizer"/>).</summary>
    public required string HomeKey { get; init; }

    /// <summary>Normalized canonical key for the away team.</summary>
    public required string AwayKey { get; init; }

    /// <summary>Null when the source lists the match as not played ("NA").</summary>
    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }

    /// <summary>Source CSV file name (provenance).</summary>
    public required string Source { get; init; }

    public string? Arena { get; init; }

    public bool Played => HomeGoals.HasValue && AwayGoals.HasValue;

    public bool Involves(string teamKey) => HomeKey == teamKey || AwayKey == teamKey;

    public string Scoreline() => Played ? $"{HomeGoals}-{AwayGoals}" : "not played";

    public override string ToString()
    {
        var date = Date?.ToString("yyyy-MM-dd") ?? "unknown date";
        var round = string.IsNullOrEmpty(Round) ? "" : $", {Round}";
        return $"{date}: {HomeTeam} {Scoreline()} {AwayTeam} ({Competition}{round})";
    }
}

/// <summary>A player row from the FIFA dataset (only the fields this server uses).</summary>
public sealed record Player
{
    public required int Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public string? Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }

    /// <summary>Normalized club key (same normalization as team names) for cross-file joins.</summary>
    public string? ClubKey { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }

    public bool IsGoalkeeper => string.Equals(Position, "GK", StringComparison.OrdinalIgnoreCase);

    /// <summary>True for attacking positions (forwards/wingers/strikers).</summary>
    public bool IsForward => Position is "ST" or "CF" or "LW" or "RW" or "LF" or "RF" or "LS" or "RS";

    public override string ToString()
    {
        var club = string.IsNullOrWhiteSpace(Club) ? "no club" : Club;
        return $"{Name} - Overall: {Overall?.ToString() ?? "?"}, Position: {Position ?? "?"}, Club: {club}";
    }
}
