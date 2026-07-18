// ============================================================================
// BrazilianSoccerMcp - Data/SoccerQueryService.cs
//
// Context block:
//   All analytical logic lives here so it is unit-testable without spinning
//   up the MCP host. The MCP tool classes are thin: they validate arguments,
//   call this service, and format the result as a human-readable string.
//
//   Conventions:
//   - Team matching uses TeamNameNormalizer.TeamMatches (accent/state-insensitive).
//   - Aggregates only count matches with a known score (Match.HasScore).
//   - Standings use 3 pts/win, 1/draw, sorted by points then GD then GF; the
//     champion is row 1 and the bottom four rows of a full Serie-A-sized
//     league are flagged as relegated (informational only — the dataset does
//     not declare relegation directly).
// ============================================================================

using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

/// <summary>Read-only query layer over <see cref="SoccerDataStore"/>.</summary>
public sealed class SoccerQueryService
{
    private readonly SoccerDataStore _store;
    public SoccerDataStore Store => _store;

    public SoccerQueryService(SoccerDataStore store) => _store = store;

    // ----------------------------------------------------------------------
    // Match queries
    // ----------------------------------------------------------------------

    public IEnumerable<Match> QueryMatches(
        string? team = null,
        string? opponent = null,
        Competition? competition = null,
        int? season = null,
        DateTime? fromDate = null,
        DateTime? toDate = null,
        string? stageContains = null)
    {
        var q = _store.Matches.AsEnumerable();
        if (competition.HasValue)
            q = q.Where(m => m.Competition == competition.Value);
        if (season.HasValue)
            q = q.Where(m => m.Season == season.Value);
        if (fromDate.HasValue)
            q = q.Where(m => m.Date >= fromDate.Value);
        if (toDate.HasValue)
            q = q.Where(m => m.Date <= toDate.Value);
        if (!string.IsNullOrWhiteSpace(team))
        {
            var t = team;
            q = q.Where(m => TeamNameNormalizer.TeamMatches(m.HomeTeam, t) ||
                             TeamNameNormalizer.TeamMatches(m.AwayTeam, t));
        }
        if (!string.IsNullOrWhiteSpace(opponent))
        {
            var o = opponent;
            q = q.Where(m => TeamNameNormalizer.TeamMatches(m.HomeTeam, o) ||
                             TeamNameNormalizer.TeamMatches(m.AwayTeam, o));
        }
        if (!string.IsNullOrWhiteSpace(stageContains))
        {
            var s = stageContains.ToLowerInvariant();
            q = q.Where(m => m.Stage != null && m.Stage.ToLowerInvariant().Contains(s));
        }
        return q;
    }

    // ----------------------------------------------------------------------
    // Head-to-head
    // ----------------------------------------------------------------------

    public HeadToHead GetHeadToHead(string teamA, string teamB, Competition? competition = null)
    {
        var matches = QueryMatches(team: teamA, opponent: teamB, competition: competition)
            .OrderBy(m => m.Date)
            .ToList();

        int winsA = 0, winsB = 0, draws = 0;
        foreach (var m in matches)
        {
            if (!m.HasScore) continue;
            // Determine which side is A.
            bool aIsHome = TeamNameNormalizer.TeamMatches(m.HomeTeam, teamA);
            bool aIsAway = TeamNameNormalizer.TeamMatches(m.AwayTeam, teamA);
            if (!aIsHome && !aIsAway) continue;
            var outcome = m.Outcome;
            bool aWins = aIsHome ? outcome == MatchOutcome.HomeWin : outcome == MatchOutcome.AwayWin;
            bool bWins = aIsHome ? outcome == MatchOutcome.AwayWin : outcome == MatchOutcome.HomeWin;
            if (aWins) winsA++;
            else if (bWins) winsB++;
            else if (outcome == MatchOutcome.Draw) draws++;
        }

        return new HeadToHead
        {
            TeamA = teamA, TeamB = teamB,
            Total = matches.Count,
            WinsA = winsA, WinsB = winsB, Draws = draws,
            Matches = matches,
        };
    }

    // ----------------------------------------------------------------------
    // Team statistics
    // ----------------------------------------------------------------------

    public TeamStats GetTeamStatistics(
        string team, int? season = null, Competition? competition = null, Venue venue = Venue.Either)
    {
        var matches = QueryMatches(team: team, competition: competition, season: season)
            .Where(m => m.HasScore);

        int w = 0, d = 0, l = 0, gf = 0, ga = 0, count = 0;
        foreach (var m in matches)
        {
            bool isHome = TeamNameNormalizer.TeamMatches(m.HomeTeam, team);
            // For venue filter: Home => only matches where team is home, etc.
            if (venue == Venue.Home && !isHome) continue;
            if (venue == Venue.Away && isHome) continue;

            int teamGoals = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            int oppGoals = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;
            gf += teamGoals; ga += oppGoals; count++;
            if (teamGoals > oppGoals) w++;
            else if (teamGoals < oppGoals) l++;
            else d++;
        }

        return new TeamStats
        {
            Team = team, Season = season, Competition = competition, Venue = venue,
            Matches = count, Wins = w, Draws = d, Losses = l,
            GoalsFor = gf, GoalsAgainst = ga,
        };
    }

    // ----------------------------------------------------------------------
    // Standings (computed from match results)
    // ----------------------------------------------------------------------

    public IReadOnlyList<StandingRow> GetStandings(Competition competition, int season)
    {
        var matches = QueryMatches(competition: competition, season: season)
            .Where(m => m.HasScore).ToList();

        var table = new Dictionary<string, StandingAcc>(StringComparer.Ordinal);
        foreach (var m in matches)
        {
            Acc(m.HomeTeam, isHome: true,  m.HomeGoals!.Value, m.AwayGoals!.Value);
            Acc(m.AwayTeam, isHome: false, m.AwayGoals!.Value, m.HomeGoals!.Value);
        }

        var rows = table.Values.Select(a => a.ToRow()).ToList();
        rows.Sort((x, y) =>
            y.Points.CompareTo(x.Points) != 0 ? y.Points.CompareTo(x.Points) :
            y.GoalDifference.CompareTo(x.GoalDifference) != 0 ? y.GoalDifference.CompareTo(x.GoalDifference) :
            y.GoalsFor.CompareTo(x.GoalsFor));

        var result = new List<StandingRow>(rows.Count);
        for (int i = 0; i < rows.Count; i++)
        {
            var r = rows[i];
            result.Add(r with
            {
                Position = i + 1,
                IsChampion = i == 0,
                Relegated = i >= rows.Count - 4 && rows.Count >= 20,
            });
        }
        return result;

        void Acc(string team, bool isHome, int gf, int ga)
        {
            if (!table.TryGetValue(team, out var a))
            {
                a = new StandingAcc(team);
                table[team] = a;
            }
            a.Played++;
            a.GoalsFor += gf; a.GoalsAgainst += ga;
            if (gf > ga) { a.Wins++; a.Points += 3; }
            else if (gf == ga) { a.Draws++; a.Points += 1; }
            else a.Losses++;
        }
    }

    private sealed class StandingAcc(string team)
    {
        public string Team { get; } = team;
        public int Points, Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst;
        public StandingRow ToRow() => new()
        {
            Team = Team, Points = Points, Played = Played, Wins = Wins,
            Draws = Draws, Losses = Losses, GoalsFor = GoalsFor, GoalsAgainst = GoalsAgainst,
        };
    }

    // ----------------------------------------------------------------------
    // Goals overview
    // ----------------------------------------------------------------------

    public GoalsOverview GetGoalsOverview(Competition? competition = null)
    {
        var matches = QueryMatches(competition: competition).Where(m => m.HasScore).ToList();
        if (matches.Count == 0)
            return new GoalsOverview { Competition = competition, Matches = 0 };

        int totalGoals = matches.Sum(m => m.HomeGoals!.Value + m.AwayGoals!.Value);
        int hw = matches.Count(m => m.Outcome == MatchOutcome.HomeWin);
        int aw = matches.Count(m => m.Outcome == MatchOutcome.AwayWin);
        int dr = matches.Count(m => m.Outcome == MatchOutcome.Draw);

        return new GoalsOverview
        {
            Competition = competition,
            Matches = matches.Count,
            AverageGoalsPerMatch = totalGoals / (double)matches.Count,
            HomeWinRate = hw * 100.0 / matches.Count,
            AwayWinRate = aw * 100.0 / matches.Count,
            DrawRate = dr * 100.0 / matches.Count,
        };
    }

    // ----------------------------------------------------------------------
    // Biggest wins
    // ----------------------------------------------------------------------

    public IReadOnlyList<Match> GetBiggestWins(Competition? competition = null, int limit = 10)
    {
        return QueryMatches(competition: competition)
            .Where(m => m.HasScore)
            .OrderByDescending(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value))
            .ThenByDescending(m => m.HomeGoals!.Value + m.AwayGoals!.Value)
            .Take(limit)
            .ToList();
    }

    // ----------------------------------------------------------------------
    // Player queries
    // ----------------------------------------------------------------------

    public IEnumerable<Player> QueryPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int? maxOverall = null)
    {
        var q = _store.Players.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(name))
        {
            var n = TeamNameNormalizer.NormalizeText(name);
            q = q.Where(p => !string.IsNullOrEmpty(p.Name) &&
                             TeamNameNormalizer.NormalizeText(p.Name).Contains(n, StringComparison.Ordinal));
        }
        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var nat = TeamNameNormalizer.NormalizeText(nationality);
            q = q.Where(p => p.Nationality != null &&
                             TeamNameNormalizer.NormalizeText(p.Nationality).Contains(nat, StringComparison.Ordinal));
        }
        if (!string.IsNullOrWhiteSpace(club))
        {
            var c = TeamNameNormalizer.NormalizeText(club);
            q = q.Where(p => p.Club != null &&
                             TeamNameNormalizer.NormalizeText(p.Club).Contains(c, StringComparison.Ordinal));
        }
        if (!string.IsNullOrWhiteSpace(position))
        {
            var pos = position.ToUpperInvariant();
            q = q.Where(p => p.Position != null &&
                             p.Position.Equals(pos, StringComparison.OrdinalIgnoreCase));
        }
        if (minOverall.HasValue)
            q = q.Where(p => p.Overall >= minOverall.Value);
        if (maxOverall.HasValue)
            q = q.Where(p => p.Overall <= maxOverall.Value);
        return q;
    }

    public IReadOnlyList<Player> GetTopPlayers(
        int limit = 10,
        string? nationality = null,
        string? club = null,
        string? position = null)
    {
        return QueryPlayers(nationality: nationality, club: club, position: position)
            .OrderByDescending(p => p.Overall ?? -1)
            .ThenBy(p => p.Name)
            .Take(limit)
            .ToList();
    }

    // ----------------------------------------------------------------------
    // Enumerations for tool prompts
    // ----------------------------------------------------------------------

    public IReadOnlyCollection<int> ListSeasons(Competition competition) =>
        _store.Matches.Where(m => m.Competition == competition && m.Season.HasValue)
            .Select(m => m.Season!.Value).Distinct().OrderBy(x => x).ToList();

    public IReadOnlyCollection<string> ListTeams(Competition? competition = null)
    {
        var q = _store.Matches.AsEnumerable();
        if (competition.HasValue) q = q.Where(m => m.Competition == competition.Value);
        var set = new HashSet<string>(StringComparer.Ordinal);
        foreach (var m in q)
        {
            set.Add(m.HomeTeam);
            set.Add(m.AwayTeam);
        }
        return set.Where(s => !string.IsNullOrEmpty(s)).OrderBy(s => s).ToList();
    }
}
