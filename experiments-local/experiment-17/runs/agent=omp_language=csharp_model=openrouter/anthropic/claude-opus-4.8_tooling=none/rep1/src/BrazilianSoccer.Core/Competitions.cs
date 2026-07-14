// -----------------------------------------------------------------------------
// File: Competitions.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Display names and free-text parsing for the Competition enum. Tool callers
//   (and ultimately an LLM) pass competition names as loose strings like
//   "Brasileirao", "serie a", "Copa do Brasil", "libertadores". This central
//   parser keeps that fuzzy mapping in one place instead of scattering string
//   comparisons through the query services.
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core;

/// <summary>Display names and fuzzy parsing for <see cref="Competition"/>.</summary>
public static class Competitions
{
    /// <summary>Human-readable name for a competition.</summary>
    public static string DisplayName(Competition c) => c switch
    {
        Competition.BrasileiraoSerieA => "Brasileirão Série A",
        Competition.BrasileiraoSerieB => "Brasileirão Série B",
        Competition.BrasileiraoSerieC => "Brasileirão Série C",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Copa Libertadores",
        _ => "Unknown competition",
    };

    /// <summary>
    /// Parses a loose competition string. Returns null when the text is empty
    /// (meaning "all competitions") and <see cref="Competition.Unknown"/> when the
    /// text is non-empty but unrecognised (so callers can report a bad filter).
    /// </summary>
    public static Competition? Parse(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return null;

        var t = TeamName.MatchKey(text); // reuse accent/case folding

        if (t.Contains("libertadores"))
            return Competition.Libertadores;
        if (t.Contains("copa do brasil") || t == "cup" || t.Contains("copa brasil"))
            return Competition.CopaDoBrasil;
        if (t.Contains("serie b") || t.Contains("serie 2") || t.Contains("segunda"))
            return Competition.BrasileiraoSerieB;
        if (t.Contains("serie c") || t.Contains("serie 3") || t.Contains("terceira"))
            return Competition.BrasileiraoSerieC;
        if (t.Contains("serie a") || t.Contains("brasileirao") || t.Contains("brasileiro")
            || t.Contains("campeonato brasileiro"))
            return Competition.BrasileiraoSerieA;

        return Competition.Unknown;
    }
}
