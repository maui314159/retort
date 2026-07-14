// ============================================================================
// File: Data/SoccerDataStore.cs
// ----------------------------------------------------------------------------
// Context: In-memory index over all loaded matches and players. Loaded once at
// host startup and injected as a singleton into every MCP tool.
//
// Provides query primitives the tools compose:
//   - MatchesForTeam / MatchesBetween (cross-dataset team matching)
//   - TeamRecordFor (W/D/L, GF/GA aggregation with venue/season/competition filters)
//   - Standings (points table for a league season)
//   - Player filtering by name/club/nationality/position
//
// The data directory is resolved by DataPaths.FindDataDir(), which walks up
// from the working directory (and from the assembly base path) looking for a
// `data/kaggle` folder. Override with the SOCCER_DATA_DIR environment variable.
// ============================================================================

using System.Globalization;
using System.Text;

namespace BrazilianSoccerMcp.Data;

public sealed class SoccerDataStore
{
    public IReadOnlyList<SoccerMatch> Matches { get; }
    public IReadOnlyList<SoccerPlayer> Players { get; }

    public SoccerDataStore(string? dataDir = null)
    {
        var dir = dataDir ?? DataPaths.FindDataDir();
        var kaggle = Path.Combine(dir, "data", "kaggle");

        var matches = new List<SoccerMatch>();
        matches.AddRange(Loaders.LoadBrasileirao(Path.Combine(kaggle, "Brasileirao_Matches.csv")));
        matches.AddRange(Loaders.LoadCopaDoBrasil(Path.Combine(kaggle, "Brazilian_Cup_Matches.csv")));
        matches.AddRange(Loaders.LoadLibertadores(Path.Combine(kaggle, "Libertadores_Matches.csv")));
        matches.AddRange(Loaders.LoadHistoricalBrasileirao(Path.Combine(kaggle, "novo_campeonato_brasileiro.csv")));
        matches.AddRange(Loaders.LoadBrFootball(Path.Combine(kaggle, "BR-Football-Dataset.csv")));
        Matches = matches;

        Players = Loaders.LoadPlayers(Path.Combine(kaggle, "fifa_data.csv"));
    }

    // ---- team matching -----------------------------------------------------

    /// <summary>All matches involving <paramref name="team"/> (home or away), de-duplicated across sources.</summary>
    public IEnumerable<SoccerMatch> MatchesForTeam(string team)
    {
        var key = TeamNameNormalizer.Parse(team);
        if (string.IsNullOrEmpty(key.Bare)) return Array.Empty<SoccerMatch>();
        return Dedupe(Matches.Where(m => TeamNameNormalizer.Matches(key, m.HomeKey) ||
                                         TeamNameNormalizer.Matches(key, m.AwayKey)));
    }

    /// <summary>Matches between two teams (either venue order), optionally filtered by competition, de-duplicated.</summary>
    public IEnumerable<SoccerMatch> MatchesBetween(string team1, string team2, string? competition = null)
    {
        var k1 = TeamNameNormalizer.Parse(team1);
        var k2 = TeamNameNormalizer.Parse(team2);
        if (string.IsNullOrEmpty(k1.Bare) || string.IsNullOrEmpty(k2.Bare))
            return Array.Empty<SoccerMatch>();

        return Dedupe(Matches.Where(m =>
            (TeamNameNormalizer.Matches(k1, m.HomeKey) && TeamNameNormalizer.Matches(k2, m.AwayKey)) ||
            (TeamNameNormalizer.Matches(k2, m.HomeKey) && TeamNameNormalizer.Matches(k1, m.AwayKey)))
            .Where(m => competition is null || CompetitionMatches(m.Competition, competition)));
    }

    /// <summary>Matches for a team within a competition and/or season.</summary>
    public IEnumerable<SoccerMatch> MatchesForTeamFiltered(
        string team, string? competition = null, int? season = null,
        DateTime? fromDate = null, DateTime? toDate = null)
    {
        return MatchesForTeam(team)
            .Where(m => competition is null || CompetitionMatches(m.Competition, competition))
            .Where(m => season is null || m.Season == season)
            .Where(m => fromDate is null || (m.Date is { } d && d >= fromDate))
            .Where(m => toDate is null || (m.Date is { } d && d <= toDate));
    }

    /// <summary>True if a stored competition label matches a user-friendly query (accent-insensitive).</summary>
    public static bool CompetitionMatches(string storedCompetition, string query)
    {
        if (string.IsNullOrWhiteSpace(query)) return true;
        return Fold(storedCompetition).Contains(Fold(query), StringComparison.OrdinalIgnoreCase);

        static string Fold(string s) =>
            s.Normalize(NormalizationForm.FormD)
             .Where(c => System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c) !=
                         System.Globalization.UnicodeCategory.NonSpacingMark)
             .Select(c => char.ToLowerInvariant(c))
             .ToArray() is { } chars
             ? new string(chars) : "";
    }

    /// <summary>Aggregate a team's W/D/L and goals over a filtered match set.</summary>
    public TeamRecord RecordForTeam(string team, IEnumerable<SoccerMatch> matches, string venue = "both")
    {
        var key = TeamNameNormalizer.Parse(team);
        int w = 0, d = 0, l = 0, gf = 0, ga = 0, count = 0;
        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.Matches(key, m.HomeKey);
            bool isAway = TeamNameNormalizer.Matches(key, m.AwayKey);
            if (!isHome && !isAway) continue;

            if (venue.Equals("home", StringComparison.OrdinalIgnoreCase) && !isHome) continue;
            if (venue.Equals("away", StringComparison.OrdinalIgnoreCase) && !isAway) continue;

            if (m.HomeGoals is null || m.AwayGoals is null) continue;
            int hg = m.HomeGoals.Value, ag = m.AwayGoals.Value;

            int teamGoals = isHome ? hg : ag;
            int oppGoals = isHome ? ag : hg;
            gf += teamGoals;
            ga += oppGoals;
            count++;

            if (teamGoals > oppGoals) w++;
            else if (teamGoals < oppGoals) l++;
            else d++;
        }
        return new TeamRecord(TeamNameNormalizer.DisplayName(key, team), count, w, d, l, gf, ga);
    }

    /// <summary>Compute a league standings table for a season (points = 3W+D).</summary>
    public List<TeamRecord> Standings(string competition, int season)
    {
        var seasonMatches = Dedupe(Matches
            .Where(m => CompetitionMatches(m.Competition, competition) && m.Season == season))
            .ToList();

        var teamKeys = new HashSet<TeamKey>(Comparer);
        foreach (var m in seasonMatches)
        {
            if (m.HomeGoals is null || m.AwayGoals is null) continue;
            teamKeys.Add(m.HomeKey);
            teamKeys.Add(m.AwayKey);
        }

        var records = new List<TeamRecord>();
        foreach (var k in teamKeys)
        {
            var rec = RecordForTeam(k.Full, seasonMatches);
            records.Add(rec with { Team = TeamNameNormalizer.DisplayName(k, k.Full) });
        }

        return records
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.Wins)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static readonly IEqualityComparer<TeamKey> Comparer = new TeamKeyComparer();

    private sealed class TeamKeyComparer : IEqualityComparer<TeamKey>
    {
        public bool Equals(TeamKey x, TeamKey y) =>
            string.Equals(x.Bare, y.Bare, StringComparison.Ordinal) &&
            string.Equals(x.Suffix ?? "", y.Suffix ?? "", StringComparison.Ordinal);
        public int GetHashCode(TeamKey obj) => HashCode.Combine(obj.Bare, obj.Suffix ?? "");
    }


    /// <summary>
    /// Remove duplicate matches recorded in multiple source files. Two matches
    /// are considered the same fixture when their normalized teams, season,
    /// date, and score all agree (so the historical Brasileirão file, the
    /// modern Brasileirão file, and the BR-Football stats file don't triple-count).
    /// </summary>
    public static IEnumerable<SoccerMatch> Dedupe(IEnumerable<SoccerMatch> matches)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var m in matches)
        {
            var sig = $"{m.HomeKey.Bare}|{m.AwayKey.Bare}|{m.Season?.ToString(CultureInfo.InvariantCulture) ?? ""}|{m.Date?.ToString("O", CultureInfo.InvariantCulture) ?? ""}|{m.HomeGoals?.ToString(CultureInfo.InvariantCulture) ?? "?"}|{m.AwayGoals?.ToString(CultureInfo.InvariantCulture) ?? "?"}";
            if (seen.Add(sig))
                yield return m;
        }
    }
    // ---- players -----------------------------------------------------------

    public IEnumerable<SoccerPlayer> SearchPlayers(
        string? name = null, string? nationality = null,
        string? club = null, string? position = null,
        int? minRating = null)
    {
        var q = Players.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(name))
        {
            var needle = FoldCI(name!);
            q = q.Where(p => FoldCI(p.Name).Contains(needle, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var needle = FoldCI(nationality!);
            q = q.Where(p => FoldCI(p.Nationality).Equals(needle, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(club))
        {
            var needle = FoldCI(club!);
            q = q.Where(p => FoldCI(p.Club).Contains(needle, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(position))
        {
            var needle = FoldCI(position!);
            q = q.Where(p => FoldCI(p.Position).Equals(needle, StringComparison.OrdinalIgnoreCase));
        }
        if (minRating is { } r)
            q = q.Where(p => p.Overall >= r);

        return q;
    }

    private static string FoldCI(string s) =>
        s.Normalize(NormalizationForm.FormD)
         .Where(c => System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c) !=
                     System.Globalization.UnicodeCategory.NonSpacingMark)
         .ToArray() is { } chars
         ? new string(chars) : "";

    // ---- listing helpers ---------------------------------------------------

    public IReadOnlyCollection<string> CompetitionsForTeam(string team)
        => MatchesForTeam(team).Select(m => m.Competition).Distinct().OrderBy(c => c).ToList();

    public IReadOnlyCollection<int> SeasonsForTeam(string team)
        => MatchesForTeam(team).Where(m => m.Season is not null).Select(m => m.Season!.Value)
            .Distinct().OrderBy(s => s).ToList();

    public DateTime? LastMatchDate(string team1, string team2)
        => MatchesBetween(team1, team2).Where(m => m.Date is not null).Max(m => m.Date);
}

/// <summary>Resolves the repository data directory containing data/kaggle/.</summary>
public static class DataPaths
{
    public static string FindDataDir()
    {
        var env = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return env;

        var candidates = new List<string> { Directory.GetCurrentDirectory() };
        candidates.Add(AppContext.BaseDirectory);
        var dir = new FileInfo(AppContext.BaseDirectory).Directory;
        while (dir is not null)
        {
            candidates.Add(dir.FullName);
            dir = dir.Parent;
        }

        foreach (var c in candidates)
        {
            if (Directory.Exists(Path.Combine(c, "data", "kaggle")))
                return c;
        }
        throw new DirectoryNotFoundException(
            "Could not locate data/kaggle. Set SOCCER_DATA_DIR to the repo root.");
    }
}
