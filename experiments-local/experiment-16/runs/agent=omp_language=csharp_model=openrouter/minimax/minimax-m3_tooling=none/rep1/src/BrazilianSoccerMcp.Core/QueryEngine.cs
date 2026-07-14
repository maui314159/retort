// =============================================================================
// Brazilian Soccer MCP Server
// File: QueryEngine.cs
// Purpose: Pure-functional read API over the loaded Dataset. No I/O, no
//          state mutation -- all methods return fresh results and are
//          safe to call concurrently from the MCP request loop.
// Context: This is the layer the MCP server projects to LLM-callable
//          tools. Every public method corresponds to one tool the LLM
//          can invoke.
// =============================================================================

using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core;

/// <summary>
/// Read API for the bundled Brazilian soccer data.
/// </summary>
public sealed class QueryEngine
{
    private readonly Dataset _data;

    public QueryEngine(Dataset data) => _data = data;

    // ---------------------------------------------------------------------
    // 1. Match queries
    // ---------------------------------------------------------------------

    /// <summary>
    /// All matches involving one of the given teams (home OR away).
    /// </summary>
    public IReadOnlyList<MatchRecord> FindMatchesByTeam(
        string team,
        int? season = null,
        Competition? competition = null,
        int limit = 200)
    {
        var key = TeamNameNormalizer.Key(team);
        if (key.Length == 0) return Array.Empty<MatchRecord>();

        var q = _data.Matches.Where(m =>
            TeamNameNormalizer.Key(m.HomeTeam) == key ||
            TeamNameNormalizer.Key(m.AwayTeam) == key);

        if (season.HasValue) q = q.Where(m => m.Season == season.Value);
        if (competition.HasValue) q = q.Where(m => m.Competition == competition.Value);

        return q.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    /// <summary>
    /// All head-to-head matches between two teams.
    /// </summary>
    public IReadOnlyList<MatchRecord> FindHeadToHead(string teamA, string teamB, int limit = 200)
    {
        var keyA = TeamNameNormalizer.Key(teamA);
        var keyB = TeamNameNormalizer.Key(teamB);
        if (keyA.Length == 0 || keyB.Length == 0) return Array.Empty<MatchRecord>();

        var q = _data.Matches.Where(m =>
            (TeamNameNormalizer.Key(m.HomeTeam) == keyA && TeamNameNormalizer.Key(m.AwayTeam) == keyB) ||
            (TeamNameNormalizer.Key(m.HomeTeam) == keyB && TeamNameNormalizer.Key(m.AwayTeam) == keyA));

        return q.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    /// <summary>
    /// Matches in a given date range (inclusive). Null bounds are open-ended.
    /// </summary>
    public IReadOnlyList<MatchRecord> FindMatchesByDate(
        DateTime? from, DateTime? to, Competition? competition = null, int limit = 200)
    {
        var q = _data.Matches.AsEnumerable();
        if (from.HasValue) q = q.Where(m => m.Date >= from.Value);
        if (to.HasValue)   q = q.Where(m => m.Date <= to.Value);
        if (competition.HasValue) q = q.Where(m => m.Competition == competition.Value);
        return q.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    /// <summary>
    /// Returns the most recent match in which the two given teams played.
    /// </summary>
    public MatchRecord? LastMatchBetween(string teamA, string teamB)
    {
        var keyA = TeamNameNormalizer.Key(teamA);
        var keyB = TeamNameNormalizer.Key(teamB);
        return _data.Matches
            .Where(m =>
                (TeamNameNormalizer.Key(m.HomeTeam) == keyA && TeamNameNormalizer.Key(m.AwayTeam) == keyB) ||
                (TeamNameNormalizer.Key(m.HomeTeam) == keyB && TeamNameNormalizer.Key(m.AwayTeam) == keyA))
            .OrderByDescending(m => m.Date)
            .Cast<MatchRecord?>()
            .FirstOrDefault();
    }

    // ---------------------------------------------------------------------
    // 2. Team queries
    // ---------------------------------------------------------------------

    /// <summary>
    /// Win/draw/loss summary for one team. Pass <paramref name="homeOrAway"/>
    /// = "Home" or "Away" to scope to that side; null gives the combined view.
    /// </summary>
    public TeamRecord? GetTeamRecord(
        string team,
        int? season = null,
        Competition? competition = null,
        string? homeOrAway = null)
    {
        var key = TeamNameNormalizer.Key(team);
        if (key.Length == 0) return null;

        var matches = _data.Matches.Where(m =>
            TeamNameNormalizer.Key(m.HomeTeam) == key ||
            TeamNameNormalizer.Key(m.AwayTeam) == key);

        if (season.HasValue) matches = matches.Where(m => m.Season == season.Value);
        if (competition.HasValue) matches = matches.Where(m => m.Competition == competition.Value);

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, played = 0;
        foreach (var m in matches)
        {
            var isHome = TeamNameNormalizer.Key(m.HomeTeam) == key;
            if (homeOrAway == "Home" && !isHome) continue;
            if (homeOrAway == "Away" && isHome) continue;

            played++;
            gf += isHome ? m.HomeGoal : m.AwayGoal;
            ga += isHome ? m.AwayGoal : m.HomeGoal;
            if (m.HomeGoal == m.AwayGoal) draws++;
            else if ((isHome && m.HomeGoal > m.AwayGoal) || (!isHome && m.AwayGoal > m.HomeGoal)) wins++;
            else losses++;
        }

        return new TeamRecord
        {
            Team = TeamNameNormalizer.DisplayName(team),
            Competition = competition?.ToString(),
            HomeOrAway = homeOrAway,
            Season = season,
            Played = played,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = gf,
            GoalsAgainst = ga,
        };
    }

    /// <summary>
    /// Aggregated head-to-head summary (W/D/L from <paramref name="teamA"/>'s
    /// point of view) plus raw match list.
    /// </summary>
    public HeadToHeadResult HeadToHead(string teamA, string teamB)
    {
        var matches = FindHeadToHead(teamA, teamB);
        int aWins = 0, bWins = 0, draws = 0;
        var keyA = TeamNameNormalizer.Key(teamA);
        foreach (var m in matches)
        {
            if (m.HomeGoal == m.AwayGoal) draws++;
            else if (TeamNameNormalizer.Key(m.HomeTeam) == keyA)
            {
                if (m.HomeGoal > m.AwayGoal) aWins++; else bWins++;
            }
            else
            {
                if (m.AwayGoal > m.HomeGoal) aWins++; else bWins++;
            }
        }
        return new HeadToHeadResult(
            TeamA: TeamNameNormalizer.DisplayName(teamA),
            TeamB: TeamNameNormalizer.DisplayName(teamB),
            AWins: aWins,
            BWins: bWins,
            Draws: draws,
            Matches: matches);
    }

    /// <summary>
    /// Computes a single-season league table for a competition.
    /// </summary>
    public IReadOnlyList<TeamStanding> GetStandings(int season, Competition competition)
    {
        var matches = _data.Matches
            .Where(m => m.Season == season && m.Competition == competition);

        // Group by team to build a map, then iterate.
        var byTeam = new Dictionary<string, TeamStandingBuilder>(StringComparer.Ordinal);
        void Add(string name, int gf, int ga, bool win)
        {
            var display = TeamNameNormalizer.DisplayName(name);
            if (!byTeam.TryGetValue(display, out var b))
            {
                b = new TeamStandingBuilder { Team = display };
                byTeam[display] = b;
            }
            b.Played++;
            b.GoalsFor += gf;
            b.GoalsAgainst += ga;
            if (win) b.Wins++;
            else if (gf == ga) b.Draws++;
            else b.Losses++;
        }

        foreach (var m in matches)
        {
            if (m.HomeGoal == m.AwayGoal)
            {
                Add(m.HomeTeam, m.HomeGoal, m.AwayGoal, win: false);
                Add(m.AwayTeam, m.AwayGoal, m.HomeGoal, win: false);
            }
            else if (m.HomeGoal > m.AwayGoal)
            {
                Add(m.HomeTeam, m.HomeGoal, m.AwayGoal, win: true);
                Add(m.AwayTeam, m.AwayGoal, m.HomeGoal, win: false);
            }
            else
            {
                Add(m.HomeTeam, m.HomeGoal, m.AwayGoal, win: false);
                Add(m.AwayTeam, m.AwayGoal, m.HomeGoal, win: true);
            }
        }

        return byTeam.Values
            .Select(b => b.Build())
            .OrderByDescending(t => t.Points)
            .ThenByDescending(t => t.Wins)
            .ThenByDescending(t => t.GoalDifference)
            .ThenBy(t => t.GoalsAgainst)
            .ToList();
    }

    // ---------------------------------------------------------------------
    // 3. Player queries
    // ---------------------------------------------------------------------

    /// <summary>
    /// Search players by free-text name match. Case-insensitive substring.
    /// </summary>
    public IReadOnlyList<PlayerRecord> SearchPlayers(
        string name, int limit = 50)
    {
        if (string.IsNullOrWhiteSpace(name)) return Array.Empty<PlayerRecord>();
        var needle = name.Trim();
        return _data.Players
            .Where(p => p.Name.Contains(needle, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Filter players by club. Substring match handles minor spelling
    /// variations across the FIFA file.
    /// </summary>
    public IReadOnlyList<PlayerRecord> PlayersByClub(string club, int limit = 100)
    {
        if (string.IsNullOrWhiteSpace(club)) return Array.Empty<PlayerRecord>();
        var needle = club.Trim();
        return _data.Players
            .Where(p => p.Club != null && p.Club.Contains(needle, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Top N Brazilian players by overall rating.
    /// </summary>
    public IReadOnlyList<PlayerRecord> TopBrazilianPlayers(int limit = 50)
    {
        return _data.Players
            .Where(p => string.Equals(p.Nationality, "Brazil", StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .ThenBy(p => p.Name)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Top N players at a given club by overall rating.
    /// </summary>
    public IReadOnlyList<PlayerRecord> TopPlayersAtClub(string club, int limit = 20)
    {
        if (string.IsNullOrWhiteSpace(club)) return Array.Empty<PlayerRecord>();
        var needle = club.Trim();
        return _data.Players
            .Where(p => p.Club != null && p.Club.Contains(needle, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Forwards only (any ST/CF/LF/RF/LW/RW position prefix) at a club.
    /// </summary>
    public IReadOnlyList<PlayerRecord> ForwardsAtClub(string club, int limit = 20)
    {
        if (string.IsNullOrWhiteSpace(club)) return Array.Empty<PlayerRecord>();
        var needle = club.Trim();
        var forwardPositions = new[] { "ST", "CF", "LF", "RF", "LW", "RW" };
        return _data.Players
            .Where(p => p.Club != null
                && p.Club.Contains(needle, StringComparison.OrdinalIgnoreCase)
                && p.Position != null
                && forwardPositions.Contains(p.Position, StringComparer.OrdinalIgnoreCase))
            .OrderByDescending(p => p.Overall ?? 0)
            .Take(limit)
            .ToList();
    }

    // ---------------------------------------------------------------------
    // 4. Statistical analysis
    // ---------------------------------------------------------------------

    /// <summary>Goals-per-match average over the given competition/season.</summary>
    public double AverageGoalsPerMatch(Competition? competition = null, int? season = null)
    {
        var q = _data.Matches.AsEnumerable();
        if (competition.HasValue) q = q.Where(m => m.Competition == competition.Value);
        if (season.HasValue) q = q.Where(m => m.Season == season.Value);
        var arr = q.ToList();
        if (arr.Count == 0) return 0.0;
        return arr.Average(m => m.HomeGoal + m.AwayGoal);
    }

    /// <summary>Home win rate (0..1) over the given scope.</summary>
    public double HomeWinRate(Competition? competition = null, int? season = null)
    {
        var q = _data.Matches.AsEnumerable();
        if (competition.HasValue) q = q.Where(m => m.Competition == competition.Value);
        if (season.HasValue) q = q.Where(m => m.Season == season.Value);
        var arr = q.ToList();
        if (arr.Count == 0) return 0.0;
        return (double)arr.Count(m => m.HomeGoal > m.AwayGoal) / arr.Count;
    }

    /// <summary>
    /// Top N biggest goal-difference wins.
    /// </summary>
    public IReadOnlyList<MatchRecord> BiggestWins(int limit = 10, Competition? competition = null)
    {
        var q = _data.Matches.AsEnumerable();
        if (competition.HasValue) q = q.Where(m => m.Competition == competition.Value);
        return q
            .OrderByDescending(m => Math.Abs(m.HomeGoal - m.AwayGoal))
            .ThenByDescending(m => m.Date)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// For each team: best away record (wins / played) above a minimum
    /// sample size, to filter out 1-match outliers.
    /// </summary>
    public IReadOnlyList<TeamRecord> BestAwayRecords(int minGames = 20, int limit = 10)
    {
        return _data.Matches
            .GroupBy(m => TeamNameNormalizer.DisplayName(m.AwayTeam))
            .Select(g =>
            {
                int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
                foreach (var m in g)
                {
                    gf += m.AwayGoal; ga += m.HomeGoal;
                    if (m.AwayGoal > m.HomeGoal) wins++;
                    else if (m.AwayGoal == m.HomeGoal) draws++;
                    else losses++;
                }
                return new TeamRecord
                {
                    Team = g.Key,
                    HomeOrAway = "Away",
                    Played = g.Count(),
                    Wins = wins,
                    Draws = draws,
                    Losses = losses,
                    GoalsFor = gf,
                    GoalsAgainst = ga,
                };
            })
            .Where(t => t.Played >= minGames)
            .OrderByDescending(t => t.WinRate)
            .ThenByDescending(t => t.Wins)
            .Take(limit)
            .ToList();
    }

    /// <summary>
    /// Find the team with the best home win rate (above minimum games).
    /// </summary>
    public IReadOnlyList<TeamRecord> BestHomeRecords(int minGames = 20, int limit = 10)
    {
        return _data.Matches
            .GroupBy(m => TeamNameNormalizer.DisplayName(m.HomeTeam))
            .Select(g =>
            {
                int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
                foreach (var m in g)
                {
                    gf += m.HomeGoal; ga += m.AwayGoal;
                    if (m.HomeGoal > m.AwayGoal) wins++;
                    else if (m.HomeGoal == m.AwayGoal) draws++;
                    else losses++;
                }
                return new TeamRecord
                {
                    Team = g.Key,
                    HomeOrAway = "Home",
                    Played = g.Count(),
                    Wins = wins,
                    Draws = draws,
                    Losses = losses,
                    GoalsFor = gf,
                    GoalsAgainst = ga,
                };
            })
            .Where(t => t.Played >= minGames)
            .OrderByDescending(t => t.WinRate)
            .ThenByDescending(t => t.Wins)
            .Take(limit)
            .ToList();
    }

    // ---------------------------------------------------------------------
    // Internals
    // ---------------------------------------------------------------------

    private sealed class TeamStandingBuilder
    {
        public string Team { get; set; } = string.Empty;
        public int Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst;
        public TeamStanding Build() => new()
        {
            Team = Team,
            Played = Played,
            Wins = Wins,
            Draws = Draws,
            Losses = Losses,
            GoalsFor = GoalsFor,
            GoalsAgainst = GoalsAgainst,
        };
    }
}

/// <summary>Result of a head-to-head query: counts plus the raw match list.</summary>
public sealed record HeadToHeadResult(
    string TeamA,
    string TeamB,
    int AWins,
    int BWins,
    int Draws,
    IReadOnlyList<MatchRecord> Matches);
