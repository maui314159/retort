using System;
using System.Collections.Generic;

namespace BrazilianSoccerMcp;

public sealed record MatchRecord(
    DateTime? Date,
    string HomeTeam,
    string AwayTeam,
    int? HomeGoals,
    int? AwayGoals,
    int Season,
    string? Round,
    string? Stage,
    string Competition,
    string Source)
{
    public bool IsHomeWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals > AwayGoals;
    public bool IsAwayWin => HomeGoals.HasValue && AwayGoals.HasValue && AwayGoals > HomeGoals;
    public bool IsDraw => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals == AwayGoals;
    public int TotalGoals => (HomeGoals ?? 0) + (AwayGoals ?? 0);
    public int GoalDifference => Math.Abs((HomeGoals ?? 0) - (AwayGoals ?? 0));
}

public sealed record Player(
    long Id,
    string Name,
    int Age,
    string Nationality,
    int Overall,
    int Potential,
    string Club,
    string Position,
    string? JerseyNumber)
{
    public string Key => $"{Name} ({Club})";
}

public sealed record TeamStatistics(
    string Team,
    int Matches,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst)
{
    public double WinRate => Matches > 0 ? (double)Wins / Matches * 100 : 0;
    public double DrawRate => Matches > 0 ? (double)Draws / Matches * 100 : 0;
    public double LossRate => Matches > 0 ? (double)Losses / Matches * 100 : 0;
}

public sealed record Standing(
    string Team,
    int Points,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst)
{
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public int MatchesPlayed => Wins + Draws + Losses;
}
