// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    QueryService.cs
// Project: BrazilianSoccer.Core
// Purpose: The knowledge-graph query engine. Operates over the in-memory
//          SoccerDataset to answer all capability categories from the spec:
//            1. Match queries  (by team, date range, competition, season)
//            2. Team queries   (records, splits, top scorers)
//            3. Player queries (name, nationality, club, ratings)
//            4. Competition queries (calculated standings, champions)
//            5. Statistical analysis (averages, biggest wins, head-to-head)
// Design:  All team matching goes through TeamNameNormalizer so the same club
//          matches regardless of spelling/suffix/accents. Methods return the
//          model value-objects in Models/; formatting lives in ResponseFormatter.
// =============================================================================

using BrazilianSoccer.Core.Data;
using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Optional filters shared by match queries.</summary>
public sealed record MatchFilter
{
    public string? Team { get; init; }
    public string? HomeTeam { get; init; }
    public string? AwayTeam { get; init; }
    public Competition? Competition { get; init; }
    public int? Season { get; init; }
    public DateTime? From { get; init; }
    public DateTime? To { get; init; }
    public int? Limit { get; init; }
}

/// <summary>Answers structured queries over the loaded dataset.</summary>
public sealed class QueryService
{
    private readonly SoccerDataset _data;

    public QueryService(SoccerDataset data) => _data = data;

    public IReadOnlyList<Match> Matches => _data.Matches;
    public IReadOnlyList<Player> Players => _data.Players;

    // ---- 1. Match queries --------------------------------------------------

    /// <summary>Returns matches satisfying the supplied filter, newest first.</summary>
    public IReadOnlyList<Match> FindMatches(MatchFilter filter)
    {
        var teamKey = Key(filter.Team);
        var homeKey = Key(filter.HomeTeam);
        var awayKey = Key(filter.AwayTeam);

        IEnumerable<Match> q = _data.Matches;

        if (teamKey is not null)
            q = q.Where(m => m.HomeTeamKey == teamKey || m.AwayTeamKey == teamKey);
        if (homeKey is not null)
            q = q.Where(m => m.HomeTeamKey == homeKey);
        if (awayKey is not null)
            q = q.Where(m => m.AwayTeamKey == awayKey);
        if (filter.Competition is { } comp)
            q = q.Where(m => m.Competition == comp);
        if (filter.Season is { } season)
            q = q.Where(m => m.Season == season);
        if (filter.From is { } from)
            q = q.Where(m => m.Date is { } d && d >= from);
        if (filter.To is { } to)
            q = q.Where(m => m.Date is { } d && d <= to);

        var ordered = q.OrderByDescending(m => m.Date ?? DateTime.MinValue).AsEnumerable();
        if (filter.Limit is { } limit && limit > 0)
            ordered = ordered.Take(limit);
        return ordered.ToList();
    }

    /// <summary>All matches between two specific teams (either venue).</summary>
    public IReadOnlyList<Match> MatchesBetween(string teamA, string teamB)
    {
        var a = Key(teamA);
        var b = Key(teamB);
        if (a is null || b is null)
            return [];
        return _data.Matches
            .Where(m => (m.HomeTeamKey == a && m.AwayTeamKey == b) ||
                        (m.HomeTeamKey == b && m.AwayTeamKey == a))
            .OrderByDescending(m => m.Date ?? DateTime.MinValue)
            .ToList();
    }

    /// <summary>Most recent match between two teams, if any.</summary>
    public Match? LastMatchBetween(string teamA, string teamB)
        => MatchesBetween(teamA, teamB).FirstOrDefault();

    // ---- 2. Team queries ---------------------------------------------------

    /// <summary>
    /// Win/draw/loss + goals record for a team over the matches matching the
    /// filter. <paramref name="venue"/>: "home", "away" or null (all).
    /// </summary>
    public TeamRecord TeamRecordFor(string team, MatchFilter? filter = null, string? venue = null)
    {
        var key = Key(team) ?? string.Empty;
        var display = _data.Matches
            .Where(m => m.HomeTeamKey == key || m.AwayTeamKey == key)
            .Select(m => m.HomeTeamKey == key ? m.HomeTeam : m.AwayTeam)
            .FirstOrDefault() ?? TeamNameNormalizer.Display(team);

        var record = new TeamRecord { Team = display };
        var matches = filter is null
            ? _data.Matches
            : FindMatches(filter with { Team = team });

        foreach (var m in matches)
        {
            var isHome = m.HomeTeamKey == key;
            var isAway = m.AwayTeamKey == key;
            if (!isHome && !isAway)
                continue;
            if (venue == "home" && !isHome) continue;
            if (venue == "away" && !isAway) continue;

            var gf = isHome ? m.HomeGoals : m.AwayGoals;
            var ga = isHome ? m.AwayGoals : m.HomeGoals;
            record.Played++;
            record.GoalsFor += gf;
            record.GoalsAgainst += ga;
            if (gf > ga) record.Wins++;
            else if (gf < ga) record.Losses++;
            else record.Draws++;
        }
        return record;
    }

    /// <summary>Head-to-head summary between two teams.</summary>
    public HeadToHead HeadToHeadFor(string teamA, string teamB)
    {
        var matches = MatchesBetween(teamA, teamB);
        var keyA = Key(teamA) ?? string.Empty;
        var displayA = matches.Select(m => m.HomeTeamKey == keyA ? m.HomeTeam : m.AwayTeam)
            .FirstOrDefault() ?? TeamNameNormalizer.Display(teamA);
        var displayB = matches.Select(m => m.HomeTeamKey == keyA ? m.AwayTeam : m.HomeTeam)
            .FirstOrDefault() ?? TeamNameNormalizer.Display(teamB);

        var h2h = new HeadToHead { TeamA = displayA, TeamB = displayB, Matches = matches };
        foreach (var m in matches)
        {
            var aIsHome = m.HomeTeamKey == keyA;
            var aGoals = aIsHome ? m.HomeGoals : m.AwayGoals;
            var bGoals = aIsHome ? m.AwayGoals : m.HomeGoals;
            h2h.TeamAGoals += aGoals;
            h2h.TeamBGoals += bGoals;
            if (aGoals > bGoals) h2h.TeamAWins++;
            else if (aGoals < bGoals) h2h.TeamBWins++;
            else h2h.Draws++;
        }
        return h2h;
    }

    // ---- 3. Player queries -------------------------------------------------

    public IReadOnlyList<Player> SearchPlayersByName(string query, int limit = 25)
    {
        if (string.IsNullOrWhiteSpace(query))
            return [];
        var q = query.Trim();
        return _data.Players
            .Where(p => p.Name.Contains(q, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    public IReadOnlyList<Player> PlayersByNationality(string nationality, int limit = 50)
    {
        if (string.IsNullOrWhiteSpace(nationality))
            return [];
        var n = nationality.Trim();
        return _data.Players
            .Where(p => string.Equals(p.Nationality, n, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    public IReadOnlyList<Player> PlayersByClub(string club, int limit = 50)
    {
        var key = Key(club);
        if (key is null)
            return [];
        return _data.Players
            .Where(p => p.ClubKey == key || (p.ClubKey.Length > 0 && p.ClubKey.Contains(key, StringComparison.Ordinal)))
            .OrderByDescending(p => p.Overall)
            .Take(limit)
            .ToList();
    }

    /// <summary>Top-rated players, optionally filtered by nationality and position.</summary>
    public IReadOnlyList<Player> TopPlayers(int limit = 10, string? nationality = null, string? position = null)
    {
        IEnumerable<Player> q = _data.Players;
        if (!string.IsNullOrWhiteSpace(nationality))
            q = q.Where(p => string.Equals(p.Nationality, nationality.Trim(), StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(position))
            q = q.Where(p => string.Equals(p.Position, position.Trim(), StringComparison.OrdinalIgnoreCase));
        return q.OrderByDescending(p => p.Overall).ThenByDescending(p => p.Potential).Take(limit).ToList();
    }

    // ---- 4. Competition queries --------------------------------------------

    /// <summary>
    /// Calculated league table for a competition+season from match results
    /// (3 pts win, 1 draw). Ordered by points, then goal difference, then
    /// goals for.
    /// </summary>
    public IReadOnlyList<StandingRow> Standings(Competition competition, int season)
    {
        var records = new Dictionary<string, TeamRecord>(StringComparer.Ordinal);

        TeamRecord Get(string key, string display)
        {
            if (!records.TryGetValue(key, out var r))
            {
                r = new TeamRecord { Team = display };
                records[key] = r;
            }
            return r;
        }

        foreach (var m in _data.Matches.Where(m => m.Competition == competition && m.Season == season))
        {
            var home = Get(m.HomeTeamKey, m.HomeTeam);
            var away = Get(m.AwayTeamKey, m.AwayTeam);
            home.Played++; away.Played++;
            home.GoalsFor += m.HomeGoals; home.GoalsAgainst += m.AwayGoals;
            away.GoalsFor += m.AwayGoals; away.GoalsAgainst += m.HomeGoals;
            switch (m.Result)
            {
                case MatchResult.HomeWin: home.Wins++; away.Losses++; break;
                case MatchResult.AwayWin: away.Wins++; home.Losses++; break;
                default: home.Draws++; away.Draws++; break;
            }
        }

        return records.Values
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.Ordinal)
            .Select((r, i) => new StandingRow { Position = i + 1, Record = r })
            .ToList();
    }

    /// <summary>Champion (top of the calculated table) for a competition+season.</summary>
    public StandingRow? Champion(Competition competition, int season)
        => Standings(competition, season).FirstOrDefault();

    public IReadOnlyList<int> SeasonsFor(Competition competition)
        => _data.Matches
            .Where(m => m.Competition == competition && m.Season.HasValue)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderBy(s => s)
            .ToList();

    // ---- 5. Statistical analysis -------------------------------------------

    public MatchStatistics ComputeStatistics(MatchFilter? filter = null)
    {
        var matches = filter is null ? _data.Matches : FindMatches(filter);
        int total = 0, goals = 0, home = 0, away = 0, draw = 0;
        foreach (var m in matches)
        {
            total++;
            goals += m.TotalGoals;
            switch (m.Result)
            {
                case MatchResult.HomeWin: home++; break;
                case MatchResult.AwayWin: away++; break;
                default: draw++; break;
            }
        }
        return new MatchStatistics
        {
            TotalMatches = total,
            TotalGoals = goals,
            HomeWins = home,
            AwayWins = away,
            Draws = draw,
        };
    }

    /// <summary>Matches with the biggest goal margin, largest first.</summary>
    public IReadOnlyList<Match> BiggestWins(MatchFilter? filter = null, int limit = 10)
    {
        var matches = filter is null ? _data.Matches : FindMatches(filter);
        return matches
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .ThenByDescending(m => m.TotalGoals)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Teams ranked by total goals scored over the filtered matches. Returns
    /// (display name, goals) descending.
    /// </summary>
    public IReadOnlyList<(string Team, int Goals)> TopScoringTeams(MatchFilter? filter = null, int limit = 10)
    {
        var matches = filter is null ? _data.Matches : FindMatches(filter);
        var goals = new Dictionary<string, (string Display, int Goals)>(StringComparer.Ordinal);
        void Add(string key, string display, int g)
        {
            (string Display, int Goals) cur = goals.GetValueOrDefault(key, (display, 0));
            goals[key] = (cur.Display, cur.Goals + g);
        }
        foreach (var m in matches)
        {
            Add(m.HomeTeamKey, m.HomeTeam, m.HomeGoals);
            Add(m.AwayTeamKey, m.AwayTeam, m.AwayGoals);
        }
        return goals.Values
            .OrderByDescending(v => v.Goals)
            .Take(limit)
            .Select(v => (v.Display, v.Goals))
            .ToList();
    }

    private static string? Key(string? team)
    {
        if (string.IsNullOrWhiteSpace(team))
            return null;
        var key = TeamNameNormalizer.Canonical(team);
        return key.Length == 0 ? null : key;
    }
}
