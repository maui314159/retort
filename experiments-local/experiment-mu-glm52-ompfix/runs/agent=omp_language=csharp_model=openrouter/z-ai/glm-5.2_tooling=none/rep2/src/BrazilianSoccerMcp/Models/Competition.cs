// ============================================================================
// BrazilianSoccerMcp - Models/Competition.cs
//
// Context block:
//   This file is part of the Brazilian Soccer MCP server. It defines the
//   Competition enumeration used to tag every match with the dataset it came
//   from, so cross-file queries can be filtered by competition.
//
//   The five datasets that contain matches map to the enum members below.
//   "Unknown" is a defensive fallback for malformed rows and is never produced
//   by the loaders but keeps switch expressions total.
// ============================================================================

namespace BrazilianSoccerMcp.Models;

/// <summary>
/// Canonical competition identifiers for the loaded match datasets.
/// </summary>
public enum Competition
{
    /// <summary>Brasileirao_Matches.csv — Serie A league matches (2012+).</summary>
    Brasileirao,

    /// <summary>Brazilian_Cup_Matches.csv — Copa do Brasil knockout cup.</summary>
    CopaDoBrasil,

    /// <summary>Libertadores_Matches.csv — Copa Libertadores.</summary>
    Libertadores,

    /// <summary>BR-Football-Dataset.csv — extended stats across many BR tournaments.</summary>
    BrFootball,

    /// <summary>novo_campeonato_brasileiro.csv — historical Serie A (2003-2019).</summary>
    HistoricoBrasileirao,

    /// <summary>Defensive fallback; never emitted by loaders.</summary>
    Unknown,
}
