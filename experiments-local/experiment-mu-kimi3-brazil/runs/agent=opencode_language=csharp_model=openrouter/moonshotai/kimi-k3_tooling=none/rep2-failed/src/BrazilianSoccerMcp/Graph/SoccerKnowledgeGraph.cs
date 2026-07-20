// Context: Brazilian Soccer MCP Server.
// In-memory knowledge graph over the unified data. Nodes: Team, Competition,
// Season, Player. Edges: PLAYED_HOME / PLAYED_AWAY (Team->Match),
// IN_COMPETITION / IN_SEASON (Match->Competition/Season), PLAYS_FOR
// (Player->Club, resolved through the same team-name normalizer so a FIFA
// club like "Grêmio" links to the same team node as "Gremio-RS").
// The query engine traverses these indexes instead of scanning 20k+ rows.
namespace BrazilianSoccerMcp.Graph;

using BrazilianSoccerMcp.Data;

public sealed class TeamNode
{
    public required string Key { get; init; }
    public required string DisplayName { get; set; }
    public List<MatchRecord> Matches { get; } = [];
    public List<PlayerRecord> Players { get; } = [];
}

public sealed class CompetitionNode
{
    public required string Name { get; init; }
    /// <summary>season -> matches, ascending by date.</summary>
    public SortedDictionary<int, List<MatchRecord>> Seasons { get; } = [];
}

public sealed class SoccerKnowledgeGraph
{
    public required IReadOnlyList<MatchRecord> AllMatches { get; init; }
    public required IReadOnlyList<PlayerRecord> AllPlayers { get; init; }
    public required Dictionary<string, TeamNode> Teams { get; init; }
    public required Dictionary<string, CompetitionNode> Competitions { get; init; }
    public required SortedSet<int> Seasons { get; init; }

    public static SoccerKnowledgeGraph Build(SoccerData data)
    {
        var teams = new Dictionary<string, TeamNode>();
        var competitions = new Dictionary<string, CompetitionNode>();
        var seasons = new SortedSet<int>();

        TeamNode TeamFor(string key)
        {
            if (!teams.TryGetValue(key, out var node))
            {
                node = new TeamNode { Key = key, DisplayName = TeamNameNormalizer.DisplayFor(key) };
                teams[key] = node;
            }
            return node;
        }

        foreach (var m in data.Matches)
        {
            TeamFor(m.HomeTeamKey).Matches.Add(m);
            TeamFor(m.AwayTeamKey).Matches.Add(m);
            if (!competitions.TryGetValue(m.Competition, out var comp))
            {
                comp = new CompetitionNode { Name = m.Competition };
                competitions[m.Competition] = comp;
            }
            if (!comp.Seasons.TryGetValue(m.Season, out var seasonMatches))
                comp.Seasons[m.Season] = seasonMatches = [];
            seasonMatches.Add(m);
            seasons.Add(m.Season);
        }

        // Apply curated display names collected by the loader (covers teams
        // that only ever appear with suffix-less spellings, e.g. "Vasco").
        foreach (var (key, display) in data.TeamNames)
            if (teams.TryGetValue(key, out var node))
                node.DisplayName = display;

        // PLAYS_FOR edges: FIFA club name -> team identity key.
        foreach (var p in data.Players)
        {
            if (p.Club is null) continue;
            var key = TeamNameNormalizer.IdentityKey(p.Club);
            if (teams.TryGetValue(key, out var club)) club.Players.Add(p);
        }

        return new SoccerKnowledgeGraph
        {
            AllMatches = data.Matches,
            AllPlayers = data.Players,
            Teams = teams,
            Competitions = competitions,
            Seasons = seasons,
        };
    }
}
