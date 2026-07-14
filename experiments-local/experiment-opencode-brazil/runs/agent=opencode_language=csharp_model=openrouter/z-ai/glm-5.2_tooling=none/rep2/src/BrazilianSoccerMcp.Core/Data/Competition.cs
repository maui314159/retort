// BrazilianSoccerMcp.Core - Domain models and data access layer for the
// Brazilian Soccer MCP server. This module unifies five match CSV datasets
// (Brasileirao, Copa do Brasil, Libertadores, BR-Football extended stats and
// the historical 2003-2019 Brasileirao) plus the FIFA player dataset into a
// single query surface used by the MCP tools.
using System.Globalization;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>
/// Canonical competition identifiers used to group matches across the
/// five provided CSV files. The <see cref="Other"/> value is used for the
/// BR-Football-Dataset whose <c>tournament</c> column contains many
/// different competitions (handled by storing the raw tournament name).
/// </summary>
public enum Competition
{
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    HistoricalBrasileirao,
    Other
}

/// <summary>
/// Helpers for converting between <see cref="Competition"/> and display
/// strings used in the formatted query responses.
/// </summary>
public static class CompetitionDisplay
{
    public static string Name(Competition c) => c switch
    {
        Competition.Brasileirao => "Brasileirao",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Copa Libertadores",
        Competition.HistoricalBrasileirao => "Brasileirao (2003-2019)",
        Competition.Other => "Other",
        _ => c.ToString()
    };
}
