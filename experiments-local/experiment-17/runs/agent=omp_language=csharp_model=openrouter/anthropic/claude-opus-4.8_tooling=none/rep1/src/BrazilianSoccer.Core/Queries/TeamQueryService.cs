// -----------------------------------------------------------------------------
// File: Queries/TeamQueryService.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Implements the "Team Queries" capability from TASK.md: a team's win/loss/draw
//   record and goals, optionally scoped by competition, season, and venue
//   (home-only / away-only / all). Backs questions like "What is Corinthians'
//   home record in 2022?" and "Compare Palmeiras and Santos head-to-head".
//
//   Records are computed from the CANONICAL match set (no double counting). Only
//   decided matches (both goals present) contribute to W/D/L and goals; the
//   Played count likewise reflects decided matches so that Wins+Draws+Losses
//   always equals Played.
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Venue filter for team-record queries.</summary>
public enum Venue
{
    /// <summary>Home and away matches.</summary>
    All,

    /// <summary>Only matches where the team played at home.</summary>
    Home,

    /// <summary>Only matches where the team played away.</summary>
    Away,
}

/// <summary>Team record and comparison queries.</summary>
public sealed class TeamQueryService
{
    private readonly SoccerDataStore _store;

    public TeamQueryService(SoccerDataStore store) => _store = store;

    /// <summary>
    /// Computes a team's record over the matches matching the supplied filters.
    /// </summary>
    public TeamRecord RecordFor(
        string team,
        Competition? competition = null,
        int? season = null,
        Venue venue = Venue.All)
    {
        int played = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;

        foreach (var m in _store.CanonicalMatches)
        {
            if (!m.HasResult)
                continue;
            if (competition is not null && m.Competition != competition)
                continue;
            if (season is not null && m.Season != season)
                continue;

            bool isHome = TeamName.Matches(m.HomeTeam, team);
            bool isAway = TeamName.Matches(m.AwayTeam, team);
            if (!isHome && !isAway)
                continue;

            // A team listed on both sides (data anomaly) is treated as home.
            if (isHome && isAway)
                isAway = false;

            if (venue == Venue.Home && !isHome) continue;
            if (venue == Venue.Away && !isAway) continue;

            int scored = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            int conceded = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;

            played++;
            gf += scored;
            ga += conceded;
            if (scored > conceded) wins++;
            else if (scored < conceded) losses++;
            else draws++;
        }

        return new TeamRecord
        {
            Team = team,
            Played = played,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = gf,
            GoalsAgainst = ga,
        };
    }

    /// <summary>
    /// Returns each team's record side by side for a head-to-head style comparison.
    /// </summary>
    public (TeamRecord A, TeamRecord B) Compare(
        string teamA,
        string teamB,
        Competition? competition = null,
        int? season = null)
        => (RecordFor(teamA, competition, season), RecordFor(teamB, competition, season));
}
