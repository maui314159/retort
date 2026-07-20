// =============================================================================
// File: Data/SoccerDatabase.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Aggregate in-memory database built once at startup and injected as a
//   singleton into every query service. Holds:
//     - all MatchRecord rows across the 5 match CSV files
//     - all PlayerRecord rows from fifa_data.csv
//     - a team → matches index (covers both home and away appearances) for
//       O(1) team-centric lookups instead of O(N) scans per query
//
// Data directory resolution:
//   The MCP server is launched from an arbitrary working directory (e.g. by
//   `claude mcp add`). ResolveDataDir walks a short list of candidates so the
//   server works whether run from the repo root, the bin output directory, or
//   an absolute override via the BRAZILIAN_SOCCER_DATA env var.
// =============================================================================
namespace BrazilianSoccerMcp.Data;

using System;
using System.Collections.Generic;
using System.IO;
using BrazilianSoccerMcp.Models;

public sealed class SoccerDatabase
{
    public IReadOnlyList<MatchRecord> Matches { get; }
    public IReadOnlyList<PlayerRecord> Players { get; }

    private readonly Dictionary<string, List<MatchRecord>> _matchesByTeam = new(StringComparer.Ordinal);

    public SoccerDatabase(string? dataDirOverride = null)
    {
        var dataDir = ResolveDataDir(dataDirOverride);
        var kaggleDir = Path.Combine(dataDir, "kaggle");
        var raw = MatchLoader.LoadAll(kaggleDir);
        Matches = DedupeMatches(raw);
        Players = PlayerLoader.Load(Path.Combine(kaggleDir, "fifa_data.csv"));

        foreach (var m in Matches)
        {
            IndexTeam(m.HomeTeamNormalized, m);
            IndexTeam(m.AwayTeamNormalized, m);
        }
    }

    /// <summary>
    /// The five match CSV files overlap heavily: the same Brasileirão fixture
    /// for (say) 2019 appears in Brasileirao_Matches.csv, novo_campeonato
    /// _brasileiro.csv, AND BR-Football-Dataset.csv. Worse, the per-source
    /// dates for the *same* fixture often disagree by a day (scheduled vs.
    /// actual, timezone offsets), so date-based dedupe leaves ~50% duplicates.
    ///
    /// The robust collapse key is the (competition, season, home, away) tuple:
    /// within a single competition+season, a given home/away pairing happens
    /// at most once (the home leg of that pair). Two-legged ties (Copa do
    /// Brasil, Libertadores group stage) keep both legs because the home team
    /// differs. Cross-competition meetings (Brasileirão + Copa do Brasil) are
    /// kept because the competition differs. Matches with no season fall back
    /// to a (competition, home, away, calendar-day) key so we don't over-merge.
    /// </summary>
    private static List<MatchRecord> DedupeMatches(List<MatchRecord> raw)
    {
        var seen = new HashSet<DedupeKey>();
        var result = new List<MatchRecord>(raw.Count);
        foreach (var m in raw)
        {
            DedupeKey key = m.Season.HasValue
                ? new DedupeKey(m.Competition, m.Season.Value, m.HomeTeamNormalized, m.AwayTeamNormalized, DateTime.MinValue)
                : new DedupeKey(m.Competition, 0, m.HomeTeamNormalized, m.AwayTeamNormalized, m.Date?.Date ?? DateTime.MinValue);
            if (!seen.Add(key)) continue;
            result.Add(m);
        }
        return result;
    }

    private readonly record struct DedupeKey(
        string Competition,
        int Season,
        string Home,
        string Away,
        DateTime DateDay);

    private void IndexTeam(string normalized, MatchRecord m)
    {
        if (string.IsNullOrEmpty(normalized)) return;
        if (!_matchesByTeam.TryGetValue(normalized, out var list))
        {
            list = new List<MatchRecord>();
            _matchesByTeam[normalized] = list;
        }
        list.Add(m);
    }

    /// <summary>All matches where the given normalized team appeared (home or away).</summary>
    public IReadOnlyList<MatchRecord> MatchesForTeam(string normalizedTeam)
    {
        return _matchesByTeam.TryGetValue(normalizedTeam, out var list)
            ? list
            : Array.Empty<MatchRecord>();
    }

    /// <summary>All distinct normalized team keys that appear in the match data.</summary>
    public IEnumerable<string> AllTeamKeys() => _matchesByTeam.Keys;

    // ---------------------------------------------------------------------
    // Data directory resolution
    // ---------------------------------------------------------------------
    public static string ResolveDataDir(string? overridePath)
    {
        if (!string.IsNullOrWhiteSpace(overridePath) && Directory.Exists(overridePath))
            return overridePath;

        var env = Environment.GetEnvironmentVariable("BRAZILIAN_SOCCER_DATA");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return env;

        // Walk up from a few roots, looking for the first ancestor that
        // contains a "data/kaggle" subtree. This makes the server work whether
        // launched from the repo root, the bin output folder, a test runner's
        // shadow-copy directory, or a subfolder of the repo.
        var roots = new List<string>
        {
            Environment.CurrentDirectory,
            AppContext.BaseDirectory,
        };
        foreach (var root in roots)
        {
            var found = WalkUpForKaggle(root);
            if (found != null) return found;
        }

        // Last resort: return the first candidate path even if it doesn't exist
        // so that a loader failure message points somewhere meaningful.
        return Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, "data"));
    }

    private static string? WalkUpForKaggle(string start)
    {
        var dir = start;
        for (int i = 0; i < 12 && !string.IsNullOrEmpty(dir); i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate)) return Path.Combine(dir, "data");
            var parent = Path.GetDirectoryName(dir) ?? "";
            if (parent == dir) break;
            dir = parent;
        }
        return null;
    }
}
