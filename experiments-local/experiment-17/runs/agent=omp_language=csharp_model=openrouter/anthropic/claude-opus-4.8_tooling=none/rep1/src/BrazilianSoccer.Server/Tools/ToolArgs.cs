// -----------------------------------------------------------------------------
// File: Tools/ToolArgs.cs
// Project: BrazilianSoccer.Server
//
// Context:
//   Shared argument parsing/validation for the MCP tools. Tool inputs arrive as
//   loose strings from the LLM, so this helper centralises:
//     - competition parsing with a clear error when the value is unrecognised
//       (vs. null meaning "all competitions"),
//     - lenient yyyy-MM-dd date parsing,
//     - building descriptive result headers that echo the active filters.
//   Keeping this out of the individual tool methods keeps those declarative.
// -----------------------------------------------------------------------------

using System.Globalization;
using BrazilianSoccer.Core;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Server.Tools;

/// <summary>Argument parsing and header building shared across MCP tools.</summary>
internal static class ToolArgs
{
    /// <summary>
    /// Parses a competition filter. Returns true with comp=null for "all", true
    /// with a concrete competition when recognised, and false with an error string
    /// when the text is non-empty but unrecognised.
    /// </summary>
    public static bool TryCompetition(string? text, out Competition? comp, out string? error)
    {
        var parsed = Competitions.Parse(text);
        if (parsed is null)
        {
            comp = null;
            error = null;
            return true;
        }
        if (parsed == Competition.Unknown)
        {
            comp = null;
            error = $"Unknown competition '{text}'. Try: Serie A / Brasileirão, " +
                    "Serie B, Serie C, Copa do Brasil, or Libertadores.";
            return false;
        }
        comp = parsed;
        error = null;
        return true;
    }

    /// <summary>Parses a yyyy-MM-dd (or general invariant) date; null when blank/invalid.</summary>
    public static DateTime? ParseDate(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return null;
        if (DateTime.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
            return d;
        return null;
    }

    /// <summary>Builds a descriptive header echoing the active match filters.</summary>
    public static string MatchHeader(string? team, string? opponent, Competition? comp, int? season)
    {
        var subject = (team, opponent) switch
        {
            ({ } t, { } o) when !string.IsNullOrWhiteSpace(t) && !string.IsNullOrWhiteSpace(o)
                => $"{t} vs {o}",
            ({ } t, _) when !string.IsNullOrWhiteSpace(t) => $"{t} matches",
            _ => "Matches",
        };

        var scope = new List<string>();
        if (comp is not null)
            scope.Add(Competitions.DisplayName(comp.Value));
        if (season is not null)
            scope.Add(season.Value.ToString(CultureInfo.InvariantCulture));

        return scope.Count == 0 ? $"{subject}:" : $"{subject} ({string.Join(", ", scope)}):";
    }
}
