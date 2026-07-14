// -----------------------------------------------------------------------------
// File: Queries/MatchQueryService.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Implements the "Match Queries" capability from TASK.md: find matches by team
//   (home/away/either), date range, competition, and season, plus head-to-head
//   between two teams and "last meeting" lookups.
//
//   All searches run over the store's CANONICAL match set (overlaps removed) so a
//   single fixture is never returned twice. Team matching is delegated to
//   TeamName.Matches, which is accent/case/suffix insensitive, so "flamengo"
//   finds "Flamengo-RJ". Results are ordered newest-first; matches without a date
//   sort last (their DateTime is treated as MinValue for ordering only).
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Read-only match search and head-to-head queries.</summary>
public sealed class MatchQueryService
{
    private readonly SoccerDataStore _store;

    public MatchQueryService(SoccerDataStore store) => _store = store;

    /// <summary>
    /// Finds matches matching every supplied (non-null) filter. A null filter is
    /// ignored. <paramref name="team"/> matches either side; <paramref name="opponent"/>,
    /// when given, requires the other side to match it (order-independent).
    /// </summary>
    public IReadOnlyList<Match> Find(
        string? team = null,
        string? opponent = null,
        Competition? competition = null,
        int? season = null,
        DateTime? from = null,
        DateTime? to = null,
        int? limit = null)
    {
        IEnumerable<Match> q = _store.CanonicalMatches;

        if (competition is not null)
            q = q.Where(m => m.Competition == competition);

        if (season is not null)
            q = q.Where(m => m.Season == season);

        if (from is not null)
            q = q.Where(m => m.Date is not null && m.Date >= from);

        if (to is not null)
            q = q.Where(m => m.Date is not null && m.Date <= to);

        if (!string.IsNullOrWhiteSpace(team) && !string.IsNullOrWhiteSpace(opponent))
        {
            q = q.Where(m =>
                (TeamName.Matches(m.HomeTeam, team) && TeamName.Matches(m.AwayTeam, opponent)) ||
                (TeamName.Matches(m.HomeTeam, opponent) && TeamName.Matches(m.AwayTeam, team)));
        }
        else if (!string.IsNullOrWhiteSpace(team))
        {
            q = q.Where(m => TeamName.Matches(m.HomeTeam, team) || TeamName.Matches(m.AwayTeam, team));
        }

        q = q.OrderByDescending(m => m.Date ?? DateTime.MinValue)
             .ThenBy(m => m.HomeTeam, StringComparer.Ordinal);

        if (limit is > 0)
            q = q.Take(limit.Value);

        return q.ToList();
    }

    /// <summary>Most recent decided match between two teams, or null if none.</summary>
    public Match? LastMeeting(string teamA, string teamB)
        => Find(teamA, teamB)
            .Where(m => m.HasResult)
            .OrderByDescending(m => m.Date ?? DateTime.MinValue)
            .FirstOrDefault();

    /// <summary>
    /// Head-to-head summary between two teams across all competitions (or a single
    /// one when <paramref name="competition"/> is supplied). Only decided matches
    /// count toward wins/draws/goals; every found match is included in the list.
    /// </summary>
    public HeadToHead HeadToHeadOf(string teamA, string teamB, Competition? competition = null)
    {
        var matches = Find(teamA, teamB, competition);

        int aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
        foreach (var m in matches)
        {
            if (!m.HasResult)
                continue;

            // teamA is "home" in this fixture when the home side matches its key.
            // Find() guarantees one side matches teamA and the other teamB, so a
            // simple home-side test is sufficient and unambiguous.
            bool aIsHome = TeamName.Matches(m.HomeTeam, teamA);

            int aGoal = aIsHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            int bGoal = aIsHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;

            aGoals += aGoal;
            bGoals += bGoal;
            if (aGoal > bGoal) aWins++;
            else if (bGoal > aGoal) bWins++;
            else draws++;
        }

        return new HeadToHead
        {
            TeamA = teamA,
            TeamB = teamB,
            TeamAWins = aWins,
            TeamBWins = bWins,
            Draws = draws,
            TeamAGoals = aGoals,
            TeamBGoals = bGoals,
            Matches = matches,
        };
    }

    /// <summary>Distinct competitions a team has appeared in (canonical set).</summary>
    public IReadOnlyList<Competition> CompetitionsFor(string team)
        => _store.CanonicalMatches
            .Where(m => TeamName.Matches(m.HomeTeam, team) || TeamName.Matches(m.AwayTeam, team))
            .Select(m => m.Competition)
            .Distinct()
            .OrderBy(c => c)
            .ToList();
}
