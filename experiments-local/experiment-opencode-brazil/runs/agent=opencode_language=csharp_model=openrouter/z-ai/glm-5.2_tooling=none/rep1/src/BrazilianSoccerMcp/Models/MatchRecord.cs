// Context block
// File: Models/MatchRecord.cs
// Purpose: Unified match record used by the Brazilian Soccer MCP server. Each of the
// five match CSV files has a different schema, so the loader maps every source to a
// single MatchRecord with optional fields (round, stage, arena, states, tournament).
// A Competition enum value identifies the originating file so queries can filter by
// competition type (Brasileirão, Copa do Brasil, Libertadores, etc.) and the merged
// BR-Football dataset (which mixes many tournaments). Goals are stored as ints; raw
// team strings are kept alongside the normalized form for display.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

namespace BrazilianSoccerMcp.Models;

/// <summary>Identifies the originating dataset for a match.</summary>
public enum Competition
{
    Unknown,
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    BrFootballDataset,
    HistoricBrasileirao,
}

/// <summary>A unified match record across all five match CSV files.</summary>
public sealed record MatchRecord
{
    public required Competition CompetitionType { get; init; }
    public required DateTime Date { get; init; }
    public required string HomeRaw { get; init; }
    public required string AwayRaw { get; init; }
    public required string Home { get; init; }
    public required string Away { get; init; }
    public required int HomeGoal { get; init; }
    public required int AwayGoal { get; init; }
    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? HomeState { get; init; }
    public string? AwayState { get; init; }
    public string? Arena { get; init; }
    public string? Tournament { get; init; }

    /// <summary>Human-readable competition label.</summary>
    public string CompetitionLabel => CompetitionType switch
    {
        Competition.Brasileirao => "Brasileirao",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Libertadores",
        Competition.BrFootballDataset => Tournament ?? "BR-Football",
        Competition.HistoricBrasileirao => "Brasileirao (2003-2019)",
        _ => "Unknown",
    };

    /// <summary>Result classification from the home team's perspective.</summary>
    public MatchOutcome Outcome =>
        HomeGoal > AwayGoal ? MatchOutcome.HomeWin :
        HomeGoal < AwayGoal ? MatchOutcome.AwayWin :
        MatchOutcome.Draw;

    /// <summary>Single-line display format.</summary>
    public string Summary =>
        $"{Date:yyyy-MM-dd}: {HomeRaw} {HomeGoal}-{AwayGoal} {AwayRaw} ({CompetitionLabel}" +
        (Round is null ? "" : $" Round {Round}") +
        (Stage is null ? "" : $" {Stage}") +
        ")";
}

/// <summary>Outcome of a match from the home team's perspective.</summary>
public enum MatchOutcome
{
    HomeWin,
    Draw,
    AwayWin,
}
