// =============================================================================
// File: Models/MatchRecord.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   A single unified match record used across all five match CSV files. Each
//   loader converts its source-specific columns into this shape so that the
//   query layer can treat every match uniformly regardless of origin file.
//
// Canonical competition bucket:
//   Competition   = the friendly bucket name surfaced to MCP clients
//                   ("Brasileirão", "Copa do Brasil", "Libertadores",
//                    "Serie B", "Serie C").
//   SourceFile    = which Kaggle CSV the row came from (for provenance).
//   Round/Stage   = kept verbatim from the source ("22", "1", "group stage").
//
// Normalization:
//   HomeTeamNormalized / AwayTeamNormalized hold the canonical key produced by
//   TeamNameNormalizer so cross-file team matching is accent/state-suffix
//   insensitive (e.g. "Palmeiras-SP" and "Palmeiras" collapse to the same key).
// =============================================================================
namespace BrazilianSoccerMcp.Models;

using System;

/// <summary>A unified match record spanning all five match CSV files.</summary>
public sealed class MatchRecord
{
    /// <summary>Friendly competition bucket surfaced to MCP clients.</summary>
    public string Competition { get; set; } = "";

    /// <summary>Source CSV file name (provenance / debugging).</summary>
    public string SourceFile { get; set; } = "";

    public DateTime? Date { get; set; }

    public string HomeTeam { get; set; } = "";
    public string AwayTeam { get; set; } = "";

    public string? HomeTeamState { get; set; }
    public string? AwayTeamState { get; set; }

    public int? HomeGoal { get; set; }
    public int? AwayGoal { get; set; }

    public int? Season { get; set; }

    public string? Round { get; set; }
    public string? Stage { get; set; }
    public string? Arena { get; set; }

    /// <summary>Canonical normalized home team key (see TeamNameNormalizer).</summary>
    public string HomeTeamNormalized { get; set; } = "";
    public string AwayTeamNormalized { get; set; } = "";

    /// <summary>True if both goals are known and the match is a complete result.</summary>
    public bool HasResult => HomeGoal.HasValue && AwayGoal.HasValue;

    /// <summary>
    /// Result classification from the perspective of <paramref name="teamNormalized"/>.
    /// Returns "win", "loss", or "draw"; null if the team did not play or no result.
    /// </summary>
    public string? ResultFor(string teamNormalized)
    {
        if (!HasResult) return null;
        bool home = string.Equals(HomeTeamNormalized, teamNormalized, StringComparison.Ordinal);
        bool away = string.Equals(AwayTeamNormalized, teamNormalized, StringComparison.Ordinal);
        if (!home && !away) return null;
        int hg = HomeGoal!.Value;
        int ag = AwayGoal!.Value;
        if (hg == ag) return "draw";
        bool homeWon = hg > ag;
        if (home) return homeWon ? "win" : "loss";
        return homeWon ? "loss" : "win";
    }
}
