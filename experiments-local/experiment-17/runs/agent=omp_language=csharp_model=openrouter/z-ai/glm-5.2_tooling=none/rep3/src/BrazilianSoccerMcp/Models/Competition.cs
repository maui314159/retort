// Brazilian Soccer MCP Server - Competition model
// Context: Enumerates the competitions represented across the bundled Kaggle CSV
// datasets. Each match record carries one of these values plus the raw
// tournament string from the source file (e.g. "Copa do Brasil",
// "Brasileirão Serie A") so callers can both filter deterministically and
// display the human-readable competition name.

namespace BrazilianSoccerMcp.Models;

/// <summary>Canonical competition buckets used for filtering and aggregation.</summary>
public enum Competition
{
    /// <summary>Brasileirão Serie A (Brasileirao_Matches.csv).</summary>
    Brasileirao,

    /// <summary>Copa do Brasil (Brazilian_Cup_Matches.csv).</summary>
    CopaDoBrasil,

    /// <summary>Copa Libertadores (Libertadores_Matches.csv).</summary>
    Libertadores,

    /// <summary>Historical Brasileirão 2003-2019 (novo_campeonato_brasileiro.csv).</summary>
    BrasileiraoHistorico,

    /// <summary>Extended match statistics dataset (BR-Football-Dataset.csv), which
    /// mixes several tournaments via the free-form "tournament" column.</summary>
    Other,
}
