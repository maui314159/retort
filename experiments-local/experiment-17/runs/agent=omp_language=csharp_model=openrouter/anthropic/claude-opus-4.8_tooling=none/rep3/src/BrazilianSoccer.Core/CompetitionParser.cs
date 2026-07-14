// =============================================================================
// File:    CompetitionParser.cs
// Project: BrazilianSoccer.Core
// Purpose: Parse free-text competition names (as an LLM or user might phrase
//          them) into the Competition enum. Returns null for "all/any".
// Context: MCP tool arguments accept a string competition; the LLM may send
//          "Brasileirao", "Serie A", "Copa do Brasil", "Libertadores", etc.
//          Centralizing the mapping keeps Tools.cs thin and consistent.
// =============================================================================

namespace BrazilianSoccer.Core;

public static class CompetitionParser
{
    /// <summary>Maps free text to a Competition, or null when unspecified/all.</summary>
    public static Competition? Parse(string? text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        var t = NameNormalizer.Key(text); // reuse accent/case folding

        if (t is "all" or "any" or "") return null;
        if (t.Contains("libertadores")) return Competition.Libertadores;
        if (t.Contains("copa") || t.Contains("cup")) return Competition.CopaDoBrasil;
        if (t.Contains("serie b")) return Competition.BrasileiraoSerieB;
        if (t.Contains("serie c")) return Competition.BrasileiraoSerieC;
        if (t.Contains("serie a") || t.Contains("brasileirao") || t.Contains("brasileiro"))
            return Competition.BrasileiraoSerieA;
        return null;
    }
}
