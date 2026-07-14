// =============================================================================
// Brazilian Soccer MCP Server
// File: Competition.cs
// Purpose: Enumerates the competitions covered by the bundled Kaggle datasets.
// Context: Used by MatchRecord to tag data origin and by query helpers to
//          filter / aggregate results without re-parsing team names.
// =============================================================================

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Competition covered by the bundled datasets.
/// </summary>
public enum Competition
{
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    BrazilianExtended, // BR-Football-Dataset.csv - multi-tournament
}
