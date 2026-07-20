using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;

namespace BrazilianSoccerMcp.Services;

/// <summary>Structured filter for match searches across the unified dataset.</summary>
public sealed record MatchFilter
{
    public string? Team { get; init; }
    public string? Opponent { get; init; }
    public string? Competition { get; init; }
    public int? Season { get; init; }
    public DateTime? From { get; init; }
    public DateTime? To { get; init; }

    /// <summary>"home" or "away" to restrict to matches at home / on the road for <see cref="Team"/>.</summary>
    public string? Venue { get; init; }

    /// <summary>Round number ("22") or cup stage ("final", "semifinals", ...).</summary>
    public string? Round { get; init; }

    public int Limit { get; init; } = 20;
}

/// <summary>Match querying plus competition-name resolution.</summary>
public sealed class MatchQueryService
{
    private readonly KnowledgeGraph _graph;
    private readonly Dictionary<int, int> _maxCupRoundBySeason = new();

    public MatchQueryService(KnowledgeGraph graph)
    {
        _graph = graph;
        foreach (var m in graph.Matches.Where(m => m.Competition == DataLoader.CopaDoBrasil && m.Season is not null))
        {
            if (m.Round is null)
                continue;
            var digits = new string(m.Round.Where(char.IsDigit).ToArray());
            if (int.TryParse(digits, out var n))
            {
                if (!_maxCupRoundBySeason.TryGetValue(m.Season!.Value, out var cur) || n > cur)
                    _maxCupRoundBySeason[m.Season!.Value] = n;
            }
        }
    }

    /// <summary>Maps free text ("brasileirao", "Serie A", "libertadores") to a canonical competition name.</summary>
    public string? ResolveCompetition(string? query)
    {
        if (string.IsNullOrWhiteSpace(query))
            return null;
        var q = TeamNameNormalizer.Normalize(query);

        if (q.Contains("libertadores", StringComparison.Ordinal))
            return DataLoader.Libertadores;
        if (q.Contains("copa do brasil", StringComparison.Ordinal))
            return DataLoader.CopaDoBrasil;
        if (q.Contains("serie b", StringComparison.Ordinal))
            return DataLoader.SerieB;
        if (q.Contains("serie c", StringComparison.Ordinal))
            return DataLoader.SerieC;
        if (q.Contains("serie a", StringComparison.Ordinal)
            || q.Contains("brasileirao", StringComparison.Ordinal)
            || q.Contains("brasileiro", StringComparison.Ordinal)
            || q is "liga" or "league")
            return DataLoader.SerieA;

        // Fallback: match against known competition names directly.
        return _graph.Competitions.FirstOrDefault(c =>
            string.Equals(TeamNameNormalizer.Normalize(c), q, StringComparison.Ordinal)
            || TeamNameNormalizer.Normalize(c).Contains(q, StringComparison.Ordinal));
    }

    /// <summary>Finds matches satisfying the filter, most recent first.</summary>
    public IReadOnlyList<Match> Find(MatchFilter filter, out List<string> notes)
    {
        notes = new List<string>();
        var query = _graph.Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(filter.Competition))
        {
            var comp = ResolveCompetition(filter.Competition);
            if (comp is null)
            {
                notes.Add($"Unknown competition '{filter.Competition}'. Known: {string.Join(", ", _graph.Competitions)}.");
                return Array.Empty<Match>();
            }
            if (!string.Equals(comp, filter.Competition, StringComparison.Ordinal))
                notes.Add($"Competition interpreted as '{comp}'.");
            query = query.Where(m => m.Competition == comp);
        }

        if (filter.Season is { } season)
            query = query.Where(m => m.Season == season);

        if (filter.From is { } from)
            query = query.Where(m => m.Date >= from);
        if (filter.To is { } to)
            query = query.Where(m => m.Date < to.Date.AddDays(1));

        string? teamKey = null;
        if (!string.IsNullOrWhiteSpace(filter.Team))
        {
            var resolution = _graph.ResolveTeam(filter.Team);
            if (!resolution.Found)
            {
                notes.Add(resolution.Note ?? "Team not found.");
                return Array.Empty<Match>();
            }
            if (resolution.Note is not null)
                notes.Add(resolution.Note);
            teamKey = resolution.Team!.Key;
            query = query.Where(m => m.Involves(teamKey));
        }

        if (!string.IsNullOrWhiteSpace(filter.Opponent))
        {
            var resolution = _graph.ResolveTeam(filter.Opponent);
            if (!resolution.Found)
            {
                notes.Add(resolution.Note ?? "Opponent not found.");
                return Array.Empty<Match>();
            }
            if (resolution.Note is not null)
                notes.Add(resolution.Note);
            var oppKey = resolution.Team!.Key;
            query = query.Where(m => m.Involves(oppKey));
        }

        if (!string.IsNullOrWhiteSpace(filter.Venue) && teamKey is not null)
        {
            query = filter.Venue.Trim().ToLowerInvariant() switch
            {
                "home" => query.Where(m => m.HomeKey == teamKey),
                "away" => query.Where(m => m.AwayKey == teamKey),
                _ => query,
            };
        }

        if (!string.IsNullOrWhiteSpace(filter.Round))
            query = query.Where(m => RoundMatches(m, filter.Round));

        return query
            .OrderByDescending(m => m.Date)
            .ThenByDescending(m => m.Season)
            .Take(filter.Limit <= 0 ? 20 : Math.Min(filter.Limit, 50_000))
            .ToList();
    }

    /// <summary>Counts matches satisfying the filter without a result cap.</summary>
    public int Count(MatchFilter filter)
    {
        var unlimited = filter with { Limit = int.MaxValue };
        return Find(unlimited, out _).Count;
    }

    private bool RoundMatches(Match m, string roundFilter)
    {
        if (m.Round is null)
            return false;
        var rf = TeamNameNormalizer.Normalize(roundFilter);
        var mr = TeamNameNormalizer.Normalize(m.Round);

        if (rf is "final" or "finals")
        {
            if (mr == "final")
                return true;
            // Copa do Brasil files number rounds; the final is the highest round of a season.
            if (m.Competition == DataLoader.CopaDoBrasil && m.Season is { } s
                && _maxCupRoundBySeason.TryGetValue(s, out var max))
                return mr == $"round {max}";
            return false;
        }

        return mr == rf || mr == $"round {rf}" || mr.Contains(rf, StringComparison.Ordinal);
    }
}
