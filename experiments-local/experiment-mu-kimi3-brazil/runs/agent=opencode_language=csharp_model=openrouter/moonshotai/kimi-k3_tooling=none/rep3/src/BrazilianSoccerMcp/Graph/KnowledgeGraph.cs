using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Graph;

/// <summary>
/// In-memory knowledge graph over the unified dataset. Nodes are teams, players,
/// competitions, seasons and matches; edges are derived relationships (team played
/// match, match in competition/season, player plays for club). The graph is
/// materialized as adjacency indexes rather than a giant edge list, which keeps
/// traversal (team -> matches -> opponents, club -> players) O(1).
/// </summary>
public sealed class KnowledgeGraph
{
    public sealed class TeamNode
    {
        public required string Key { get; init; }
        public required string DisplayName { get; set; }
        public List<Match> Matches { get; } = new();
    }

    public sealed record TeamResolution(TeamNode? Team, string? Note)
    {
        public bool Found => Team is not null;
    }

    private readonly Dictionary<string, TeamNode> _teams;
    private readonly Dictionary<string, List<Player>> _playersByClubKey;
    private readonly Dictionary<string, List<Match>> _matchesByCompetition;

    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }
    public IReadOnlyDictionary<string, int> SourceContributions { get; }
    public int TotalMatchRowsRead { get; }

    public IReadOnlyDictionary<string, TeamNode> Teams => _teams;
    public IReadOnlyDictionary<string, List<Player>> PlayersByClubKey => _playersByClubKey;
    public IReadOnlyDictionary<string, List<Match>> MatchesByCompetition => _matchesByCompetition;

    public IReadOnlyList<string> Competitions { get; }
    public IReadOnlyList<int> Seasons { get; }

    public KnowledgeGraph(DataLoader.LoadResult data)
    {
        Matches = data.Matches;
        Players = data.Players;
        SourceContributions = data.SourceContributions;
        TotalMatchRowsRead = data.TotalMatchRowsRead;

        _teams = new Dictionary<string, TeamNode>(StringComparer.Ordinal);
        foreach (var match in data.Matches)
        {
            AddTeam(match.HomeKey, match.HomeTeam).Matches.Add(match);
            AddTeam(match.AwayKey, match.AwayTeam).Matches.Add(match);
        }

        _playersByClubKey = data.Players
            .Where(p => p.ClubKey is not null)
            .GroupBy(p => p.ClubKey!, StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.OrderByDescending(p => p.Overall ?? 0).ToList(), StringComparer.Ordinal);

        _matchesByCompetition = data.Matches
            .GroupBy(m => m.Competition, StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);

        Competitions = _matchesByCompetition.Keys.Order(StringComparer.Ordinal).ToList();
        Seasons = data.Matches.Where(m => m.Season.HasValue)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderDescending()
            .ToList();
    }

    private TeamNode AddTeam(string key, string rawName)
    {
        if (!_teams.TryGetValue(key, out var node))
        {
            node = new TeamNode { Key = key, DisplayName = rawName };
            _teams[key] = node;
        }
        return node;
    }

    /// <summary>
    /// Resolves a free-form team name ("Flamengo", "Atlético Mineiro", "Palmeiras-SP")
    /// to a graph team node. Exact canonical-key match wins; otherwise prefix
    /// candidates are ranked by number of matches in the dataset, and a note is
    /// returned when the choice was ambiguous.
    /// </summary>
    public TeamResolution ResolveTeam(string? query)
    {
        if (string.IsNullOrWhiteSpace(query))
            return new TeamResolution(null, "No team name given.");

        var canon = TeamNameNormalizer.CanonKey(query);
        if (canon.Length == 0)
            return new TeamResolution(null, "No team name given.");

        if (_teams.TryGetValue(canon, out var exact))
            return new TeamResolution(exact, null);

        var candidates = _teams.Values
            .Where(t => t.Key.StartsWith(canon + " ", StringComparison.Ordinal)
                        || canon.StartsWith(t.Key + " ", StringComparison.Ordinal)
                        || t.Key.Contains(canon, StringComparison.Ordinal))
            .OrderByDescending(t => t.Matches.Count)
            .ToList();

        if (candidates.Count == 0)
            return new TeamResolution(null, $"No team matching '{query}' found in the dataset.");

        var chosen = candidates[0];
        string? note = null;
        if (candidates.Count > 1 && candidates[0].Key != canon)
        {
            var others = string.Join(", ", candidates.Skip(1).Take(3).Select(c => c.DisplayName));
            note = $"Interpreted '{query}' as {chosen.DisplayName} (other candidates: {others}).";
        }
        return new TeamResolution(chosen, note);
    }

    /// <summary>Node/edge counts, exposed via the graph_stats tool.</summary>
    public (int TeamNodes, int PlayerNodes, int CompetitionNodes, int SeasonNodes, int MatchNodes, long Edges) Stats()
    {
        var seasonNodes = Matches.Where(m => m.Season.HasValue).Select(m => m.Season!.Value).Distinct().Count();
        var clubLinks = Players.Count(p => p.ClubKey is not null && _teams.ContainsKey(p.ClubKey));
        // Each match contributes 4 edges (home team, away team, competition, season).
        long edges = (long)Matches.Count * 4 + clubLinks;
        return (_teams.Count, Players.Count, Competitions.Count, seasonNodes, Matches.Count, edges);
    }
}
