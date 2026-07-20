// BrazilianSoccerMcp.Core / Normalization / TeamNormalizer.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. TASK.md "Data Quality Notes -> Team Name
// Variations" calls out that the same club appears as "Palmeiras-SP", "Palmeiras",
// and "Sport Club Corinthians Paulista" across files. Without normalization,
// cross-file queries silently miss rows; but OVER-normalization is worse: naively
// stripping the "-UF" suffix merges distinct clubs that share a base name
// (Atlético-MG, -GO, -PR all collapse to "atletico" — observed in the real data,
// producing a bogus 76-match "champion"). The state suffix is DISAMBIGUATING, not
// noise, so we keep it.
// Canonicalization (Normalize):
//   1. Lowercase (invariant culture).
//   2. Strip parenthesized fragments ("(antigo Esporte Clube Barreira)").
//   3. Accent-fold: "São Paulo" -> "sao paulo", "Avaí" -> "avai".
//   4. Normalize dash spacing: "América - MG" -> "america-mg" so suffix checks work.
//   5. Collapse whitespace, strip residual punctuation EXCEPT the hyphen (so the
//      "-UF" suffix survives).
//   Result keeps the suffix: "Palmeiras-SP" -> "palmeiras-sp", "Flamengo-RJ" ->
//   "flamengo-rj", "Atletico-MG" / "Atletico-GO" / "Atletico-PR" stay distinct.
// Matching (SameTeam): suffix-tolerant. A suffix-less query "palmeiras" matches a
// stored "palmeiras-sp" because the stored key is the query plus a valid 2-letter
// Brazilian UF. This lets a user (or FIFA Club field) say "Flamengo" and still
// match the data's "flamengo-rj", while NEVER merging Atlético-MG with -GO.
// -----------------------------------------------------------------------------

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Core.Normalization;

/// <summary>
/// Normalizes Brazilian club names into a canonical, matchable key, and provides
/// suffix-tolerant matching so distinct same-base clubs never collide.
/// </summary>
public static class TeamNormalizer
{
    /// <summary>Two-letter codes for all 27 Brazilian federative units (UFs).</summary>
    private static readonly HashSet<string> BrazilianStateCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
        "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
    };

    private static readonly Regex ParenthesizedRegex = new(@"\([^)]*\)", RegexOptions.Compiled);
    // Punctuation EXCEPT hyphen: keep the "-UF" suffix intact.
    private static readonly Regex PunctuationRegex = new(@"[^\p{L}\p{N}\s\-]", RegexOptions.Compiled);
    // Collapse spaces around hyphens (any dash kind) so "- MG" -> "-mg".
    private static readonly Regex DashSpacingRegex = new(@"\s*[\-‐-―]\s*", RegexOptions.Compiled);
    private static readonly Regex WhitespaceRegex = new(@"\s+", RegexOptions.Compiled);

    /// <summary>
    /// Returns the canonical team key for <paramref name="raw"/>. Deterministic and
    /// idempotent. Keeps the trailing Brazilian UF suffix so distinct same-base
    /// clubs (Atlético-MG/-GO/-PR) do NOT collide.
    /// </summary>
    public static string Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        // 1. Lowercase invariant.
        var s = raw.Trim().ToLowerInvariant();

        // 2. Strip parenthesized fragments.
        s = ParenthesizedRegex.Replace(s, " ");

        // 3. Accent-fold.
        s = RemoveAccents(s);

        // 4. Normalize dash spacing -> single ASCII hyphen.
        s = DashSpacingRegex.Replace(s, "-");

        // 5. Strip residual punctuation (keep hyphens + alphanumerics + spaces).
        s = PunctuationRegex.Replace(s, " ");

        // 6. Collapse whitespace, trim, trim stray leading/trailing hyphens.
        s = WhitespaceRegex.Replace(s, " ").Trim();
        s = s.Trim('-').Trim();
        s = WhitespaceRegex.Replace(s, " ").Trim();
        // Collapse any " - " artefacts back to "-" after the punctuation pass.
        s = s.Replace(" - ", "-").Replace("- ", "-").Replace(" -", "-");

        return s;
    }

    /// <summary>
    /// Suffix-tolerant same-club test between two CANONICAL keys. Returns true when
    /// <paramref name="storedKey"/> and <paramref name="queryKey"/> refer to the
    /// same club: exact match, OR one is the other plus a valid 2-letter Brazilian
    /// UF suffix. Distinct clubs sharing a base name (Atlético-MG vs -GO) never
    /// match because both retain their suffixes.
    /// </summary>
    public static bool SameTeam(string storedKey, string queryKey)
    {
        if (string.IsNullOrEmpty(storedKey) || string.IsNullOrEmpty(queryKey))
            return false;
        if (string.Equals(storedKey, queryKey, StringComparison.Ordinal))
            return true;
        return IsQuerySuffixOf(storedKey, queryKey) || IsQuerySuffixOf(queryKey, storedKey);
    }

    /// <summary>
    /// True when <paramref name="longer"/> == <paramref name="shorter"/> + "-" + a
    /// valid 2-letter Brazilian UF. Used to match a suffix-less query ("palmeiras")
    /// against a suffixed stored key ("palmeiras-sp").
    /// </summary>
    private static bool IsQuerySuffixOf(string longer, string shorter)
    {
        const int suffixLen = 3; // "-XX"
        if (longer.Length != shorter.Length + suffixLen)
            return false;
        if (!longer.StartsWith(shorter + "-", StringComparison.Ordinal))
            return false;
        var uf = longer.AsSpan(shorter.Length + 1, 2);
        return IsValidStateCode(uf);
    }

    private static bool IsValidStateCode(ReadOnlySpan<char> code)
    {
        if (code.Length != 2) return false;
        // Convert span to string for the HashSet lookup (2 chars, cheap).
        return BrazilianStateCodes.Contains(code.ToString());
    }

    /// <summary>
    /// Accent-fold for matching. "São Paulo" -> "Sao Paulo", "Avaí" -> "Avai".
    /// NFKD decomposes accented characters, then drops combining marks.
    /// </summary>
    public static string RemoveAccents(string s)
    {
        if (string.IsNullOrEmpty(s)) return s;
        var normalized = s.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(s.Length);
        foreach (var ch in normalized)
        {
            var uc = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (uc != UnicodeCategory.NonSpacingMark &&
                uc != UnicodeCategory.SpacingCombiningMark &&
                uc != UnicodeCategory.EnclosingMark)
            {
                sb.Append(ch);
            }
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
