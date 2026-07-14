// Context block
// File: Services/CompetitionService.cs
// Purpose: Competition-level queries for the Brazilian Soccer MCP server. Computes
// league standings for the Brasileirão (modern 2012+ file and the historic 2003-2019
// file) by summing points, wins, draws, losses, goals for/against/difference over a
// given season. Standings are sorted by points, then goal difference, then goals for.
// Also returns the champion and a top-N summary. Cup and Libertadores standings are not
// meaningful from match files alone, so the service focuses on the league competitions.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Competition-level queries (standings, champions).</summary>
public sealed class CompetitionService
{
    private readonly SoccerDataStore _store;
    private readonly MatchService _matches;

    public CompetitionService(SoccerDataStore store, MatchService matches)
    {
        _store = store;
        _matches = matches;
    }

    /// <summary>Computes Brasileirão standings for a season, merging modern and historic data.</summary>
    public List<StandingRow> GetBrasileiraoStandings(int season, int topN = 50)
    {
        var rows = ComputeStandings(season, Competition.Brasileirao);
        if (rows.Count == 0)
        {
            // Fall back to the historic dataset when the season predates the modern file.
            rows = ComputeStandings(season, Competition.HistoricBrasileirao);
        }
        return TopN(rows, topN);
    }

    /// <summary>Returns the champion for a season, or null when standings are empty.</summary>
    public StandingRow? GetChampion(int season)
    {
        var standings = GetBrasileiraoStandings(season, topN: 1);
        return standings.FirstOrDefault();
    }

    private List<StandingRow> ComputeStandings(int season, Competition competition)
    {
        var matches = _matches.SearchMatches(season: season, competition: competition);
        var map = new Dictionary<string, StandingAccumulator>(StringComparer.OrdinalIgnoreCase);
        foreach (var m in matches)
        {
            var home = _store.Normalizer.Normalize(m.Home);
            var away = _store.Normalizer.Normalize(m.Away);
            Accumulate(map, home, m.HomeGoal, m.AwayGoal, true);
            Accumulate(map, away, m.AwayGoal, m.HomeGoal, false);
        }
        var rows = map.Values.Select(a => a.ToRow()).ToList();
        rows.Sort(StandingRow.Compare);
        for (int i = 0; i < rows.Count; i++)
        {
            rows[i] = rows[i] with { Position = i + 1 };
        }
        return rows;
    }

    private static void Accumulate(Dictionary<string, StandingAccumulator> map, string team, int gf, int ga, bool isHome)
    {
        if (string.IsNullOrWhiteSpace(team))
        {
            return;
        }
        if (!map.TryGetValue(team, out var acc))
        {
            acc = new StandingAccumulator(team);
            map[team] = acc;
        }
        acc.Played++;
        acc.GoalsFor += gf;
        acc.GoalsAgainst += ga;
        if (isHome) acc.HomePlayed++;
        if (gf > ga) { acc.Wins++; if (isHome) acc.HomeWins++; acc.Points += 3; }
        else if (gf < ga) { acc.Losses++; if (isHome) acc.HomeLosses++; }
        else { acc.Draws++; acc.Points++; if (isHome) acc.HomeDraws++; }
    }

    private static List<StandingRow> TopN(List<StandingRow> rows, int topN)
    {
        if (topN <= 0 || rows.Count <= topN) return rows;
        return rows.GetRange(0, topN);
    }

    private sealed class StandingAccumulator
    {
        public StandingAccumulator(string team) => Team = team;
        public string Team { get; }
        public int Points { get; set; }
        public int Played { get; set; }
        public int Wins { get; set; }
        public int Draws { get; set; }
        public int Losses { get; set; }
        public int GoalsFor { get; set; }
        public int GoalsAgainst { get; set; }
        public int HomePlayed { get; set; }
        public int HomeWins { get; set; }
        public int HomeDraws { get; set; }
        public int HomeLosses { get; set; }

        public StandingRow ToRow() => new(0, Team, Points, Played, Wins, Draws, Losses,
            GoalsFor, GoalsAgainst, GoalsFor - GoalsAgainst);
    }
}

/// <summary>A single row in a computed standings table.</summary>
public sealed record StandingRow(
    int Position,
    string Team,
    int Points,
    int Played,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    int GoalDifference)
{
    public static int Compare(StandingRow a, StandingRow b)
    {
        var byPoints = b.Points.CompareTo(a.Points);
        if (byPoints != 0) return byPoints;
        var byGd = b.GoalDifference.CompareTo(a.GoalDifference);
        if (byGd != 0) return byGd;
        var byGf = b.GoalsFor.CompareTo(a.GoalsFor);
        if (byGf != 0) return byGf;
        return string.Compare(a.Team, b.Team, StringComparison.OrdinalIgnoreCase);
    }
}
