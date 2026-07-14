// =============================================================================
// File:    Models.cs
// Project: BrazilianSoccer.Core
// Purpose: Domain model for the Brazilian Soccer knowledge graph. Defines the
//          unified Match and Player records that every CSV source is mapped
//          onto, plus the aggregate result types (TeamRecord, HeadToHead,
//          Standing, MatchResult) returned by the query engine.
// Context: All six Kaggle CSVs use different shapes (state suffixes on team
//          names, ISO vs DD/MM/YYYY dates, quoted goal columns). Loaders
//          (see DataLoader.cs) normalize each row into the single Match shape
//          here so the query engine (SoccerDatabase.cs) is source-agnostic.
//          Team names are stored both raw (as printed) and normalized (a
//          fold key from NameNormalizer) so lookups survive accents/suffixes.
// =============================================================================

namespace BrazilianSoccer.Core;

/// <summary>The competitions represented across the provided datasets.</summary>
public enum Competition
{
    Unknown = 0,
    BrasileiraoSerieA,
    BrasileiraoSerieB,
    BrasileiraoSerieC,
    CopaDoBrasil,
    Libertadores,
}

public static class CompetitionExtensions
{
    public static string DisplayName(this Competition c) => c switch
    {
        Competition.BrasileiraoSerieA => "Brasileirão Série A",
        Competition.BrasileiraoSerieB => "Brasileirão Série B",
        Competition.BrasileiraoSerieC => "Brasileirão Série C",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Copa Libertadores",
        _ => "Unknown",
    };
}

public enum MatchOutcome { HomeWin, AwayWin, Draw }

/// <summary>
/// One football match unified across every source file. Goals may be null when
/// a source row is missing a score; <see cref="HasScore"/> guards aggregation.
/// </summary>
public sealed record Match
{
    public required Competition Competition { get; init; }
    public required string Source { get; init; }

    public DateTime? Date { get; init; }
    public int Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? Venue { get; init; }

    /// <summary>Home team name as it appears in the source (suffix-stripped, accents kept).</summary>
    public required string HomeTeam { get; init; }
    /// <summary>Away team name as it appears in the source (suffix-stripped, accents kept).</summary>
    public required string AwayTeam { get; init; }
    /// <summary>Fold key for the home team used for matching (accent/suffix/case insensitive).</summary>
    public required string HomeKey { get; init; }
    /// <summary>Fold key for the away team used for matching.</summary>
    public required string AwayKey { get; init; }

    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }

    // Extended stats — only populated from BR-Football-Dataset.csv.
    public int? HomeShots { get; init; }
    public int? AwayShots { get; init; }
    public int? HomeCorners { get; init; }
    public int? AwayCorners { get; init; }

    public bool HasScore => HomeGoals.HasValue && AwayGoals.HasValue;

    public MatchOutcome? Outcome => HasScore
        ? (HomeGoals!.Value > AwayGoals!.Value ? MatchOutcome.HomeWin
            : HomeGoals.Value < AwayGoals.Value ? MatchOutcome.AwayWin
            : MatchOutcome.Draw)
        : null;

    public int TotalGoals => HasScore ? HomeGoals!.Value + AwayGoals!.Value : 0;
}

/// <summary>A FIFA player record from fifa_data.csv.</summary>
public sealed class Player
{
    public int Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public string Nationality { get; init; } = "";
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = "";
    public string Position { get; init; } = "";
    public int? JerseyNumber { get; init; }
    public string Height { get; init; } = "";
    public string Weight { get; init; } = "";

    /// <summary>Fold key for the club, used for club filtering.</summary>
    public required string ClubKey { get; init; }
    /// <summary>Fold key for the player name, used for name search.</summary>
    public required string NameKey { get; init; }
}

/// <summary>Win/draw/loss + goals aggregate for a team over a filtered set of matches.</summary>
public sealed class TeamRecord
{
    public required string Team { get; init; }
    public int Played { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }

    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Played == 0 ? 0 : (double)Wins / Played;

    public void Add(bool win, bool draw, int goalsFor, int goalsAgainst)
    {
        Played++;
        if (win) Wins++;
        else if (draw) Draws++;
        else Losses++;
        GoalsFor += goalsFor;
        GoalsAgainst += goalsAgainst;
    }
}

/// <summary>Head-to-head summary between two teams plus the underlying matches.</summary>
public sealed class HeadToHead
{
    public required string TeamA { get; init; }
    public required string TeamB { get; init; }
    public int TeamAWins { get; set; }
    public int TeamBWins { get; set; }
    public int Draws { get; set; }
    public int TeamAGoals { get; set; }
    public int TeamBGoals { get; set; }
    public required IReadOnlyList<Match> Matches { get; init; }

    public int Played => Matches.Count;
}

/// <summary>One row of a calculated league table.</summary>
public sealed class Standing
{
    public int Position { get; set; }
    public required TeamRecord Record { get; init; }
}
