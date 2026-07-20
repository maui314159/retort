// BrazilianSoccerMcp.Core / Queries / TeamQueries.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Implements TASK.md "Required Capabilities
// 2. Team Queries": match history & statistics, W/L/D records, goals scored/
// conceded, performance by competition, home vs away splits, side-by-side
// comparison, and top-scorers rankings.
// Team matching: uses the suffix-tolerant key-set resolution (see SoccerDataService.
// ResolveTeamKeys) so a query "Palmeiras" gathers both "palmeiras-sp" and
// "palmeiras" forms across files without merging distinct same-base clubs.
// W/D/L math: for each scored match in the filtered scope where the team's
// canonical key is on either side, attribute goals by which side the team is on.
// Un-scored rows are excluded from W/D/L and goals (surfaced honestly via Matches).
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Queries;

public enum Venue { Both, Home, Away }

/// <summary>Team history & aggregate-record queries.</summary>
public sealed class TeamQueries
{
    private readonly SoccerDataService _data;
    public TeamQueries(SoccerDataService data) => _data = data;

    /// <summary>
    /// Computes the win/draw/loss + goals record for a team within an optional
    /// (competition, season, date range, venue) scope.
    /// </summary>
    public TeamRecord TeamRecord(
        string team,
        CompetitionKind? competition = null,
        int? season = null,
        Venue venue = Venue.Both,
        DateTime? from = null,
        DateTime? until = null)
    {
        var keys = _data.ResolveTeamKeys(team);
        if (keys.Count == 0)
            return new TeamRecord { Team = team ?? string.Empty };
        var set = new HashSet<string>(keys, StringComparer.Ordinal);

        var scoredMatches = _data.Matches
            .Where(m => !competition.HasValue || m.Competition == competition.Value)
            .Where(m => !season.HasValue || (m.Season.HasValue && m.Season.Value == season.Value))
            .Where(m => !from.HasValue || (m.Date.HasValue && m.Date.Value >= from.Value))
            .Where(m => !until.HasValue || (m.Date.HasValue && m.Date.Value <= until.Value))
            .Where(m => set.Contains(m.HomeTeam) || set.Contains(m.AwayTeam))
            .ToList();

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, scored = 0;
        foreach (var m in scoredMatches)
        {
            if (!m.HasScore) continue;
            var isHome = set.Contains(m.HomeTeam);
            if (venue != Venue.Both)
            {
                var venueIsHome = venue == Venue.Home;
                if (isHome != venueIsHome) continue;
            }
            scored++;
            int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
            int teamGoals = isHome ? hg : ag;
            int oppGoals = isHome ? ag : hg;
            gf += teamGoals;
            ga += oppGoals;
            if (teamGoals > oppGoals) wins++;
            else if (teamGoals < oppGoals) losses++;
            else draws++;
        }

        return new TeamRecord
        {
            Team = keys.First(),
            Matches = scored,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = gf,
            GoalsAgainst = ga,
        };
    }

    /// <summary>
    /// Side-by-side comparison of two teams across the same scope (TASK.md
    /// "Compare Palmeiras and Santos head-to-head").
    /// </summary>
    public (TeamRecord a, TeamRecord b, HeadToHead h2h) Compare(
        string teamA, string teamB,
        CompetitionKind? competition = null, int? season = null)
    {
        var a = TeamRecord(teamA, competition, season);
        var b = TeamRecord(teamB, competition, season);
        var matchQueries = new MatchQueries(_data);
        var filter = new MatchFilter { Competition = competition, Season = season };
        var h2h = matchQueries.HeadToHead(teamA, teamB, filter);
        return (a, b, h2h);
    }

    /// <summary>
    /// Returns the team(s) scoring the most goals in a competition+season scope.
    /// Useful for "Which team scored the most goals in Serie A 2023?".
    /// Grouping uses each match row's stored canonical key, so distinct same-base
    /// clubs (Atlético-MG vs -GO) accrue separately.
    /// </summary>
    public IReadOnlyList<(string Team, int GoalsFor)> TopScoringTeams(
        CompetitionKind competition, int season, int limit = 10)
    {
        var matches = _data.Matches
            .Where(m => m.Competition == competition && m.Season.HasValue && m.Season.Value == season)
            .ToList();

        var goalsByTeam = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var m in matches)
        {
            if (!m.HasScore) continue;
            goalsByTeam.TryGetValue(m.HomeTeam, out var hg); goalsByTeam[m.HomeTeam] = hg + m.HomeGoals!.Value;
            goalsByTeam.TryGetValue(m.AwayTeam, out var ag); goalsByTeam[m.AwayTeam] = ag + m.AwayGoals!.Value;
        }
        return goalsByTeam
            .OrderByDescending(kv => kv.Value)
            .ThenBy(kv => kv.Key)
            .Take(limit)
            .Select(kv => (kv.Key, kv.Value))
            .ToList();
    }
}
