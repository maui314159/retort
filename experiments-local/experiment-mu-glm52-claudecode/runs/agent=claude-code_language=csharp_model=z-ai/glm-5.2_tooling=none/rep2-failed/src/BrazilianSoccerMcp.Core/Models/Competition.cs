// BrazilianSoccerMcp.Core / Models / Competition.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server (see TASK.md / brazilian-soccer-mcp-guide.md).
// Purpose: Enumerates the competitions represented across the six source CSVs.
//   - BrasileiraoSerieA   -> data/kaggle/Brasileirao_Matches.csv
//   - CopaDoBrasil         -> data/kaggle/Brazilian_Cup_Matches.csv
//   - CopaLibertadores     -> data/kaggle/Libertadores_Matches.csv
//   - HistoricoBrasileirao -> data/kaggle/novo_campeonato_brasileiro.csv (2003-2019)
//   - Extended             -> data/kaggle/BR-Football-Dataset.csv (mixed tournaments,
//                             carries corners/shots/attacks enrichment)
//   - Other                -> any tournament name in the extended dataset that the
//                             loader cannot classify into one of the above.
// The string fallback on `Other` preserves the original tournament label so the
// knowledge surface never silently loses information.
// -----------------------------------------------------------------------------

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Canonical competition identifiers used across all match datasets.
/// </summary>
public enum CompetitionKind
{
    BrasileiraoSerieA,
    CopaDoBrasil,
    CopaLibertadores,
    HistoricoBrasileirao,
    Extended,
    Other
}

/// <summary>
/// Resolves free-text tournament names from the extended BR-Football dataset into a
/// canonical <see cref="CompetitionKind"/>. Matching is accent- and case-insensitive
/// because the source file uses unaccented names ("Copa do Brasil", "Libertadores").
/// </summary>
public static class CompetitionResolver
{
    public static CompetitionKind Resolve(string? tournament)
    {
        if (string.IsNullOrWhiteSpace(tournament))
            return CompetitionKind.Other;

        var key = tournament.Trim().ToLowerInvariant();
        return key switch
        {
            "brasileirao" or "brasileirão" or "serie a" or "série a" => CompetitionKind.BrasileiraoSerieA,
            "copa do brasil" => CompetitionKind.CopaDoBrasil,
            "libertadores" or "copa libertadores" => CompetitionKind.CopaLibertadores,
            _ => CompetitionKind.Other
        };
    }
}
