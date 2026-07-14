/**
 * Team-level aggregates: win/loss/draw, head-to-head, season records.
 */

import type { Competition, DatasetSnapshot, Match } from '../data/types.js';
import { teamMatches } from '../data/normalizer.js';
import { findMatches, type MatchQuery } from './matches.js';

export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  homeMatches: number;
  homeWins: number;
  homeDraws: number;
  homeLosses: number;
  homeGoalsFor: number;
  homeGoalsAgainst: number;
  awayMatches: number;
  awayWins: number;
  awayDraws: number;
  awayLosses: number;
  awayGoalsFor: number;
  awayGoalsAgainst: number;
  perCompetition: Record<string, { matches: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number }>;
}

export function emptyRecord(): TeamRecord {
  return {
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    homeMatches: 0, homeWins: 0, homeDraws: 0, homeLosses: 0, homeGoalsFor: 0, homeGoalsAgainst: 0,
    awayMatches: 0, awayWins: 0, awayDraws: 0, awayLosses: 0, awayGoalsFor: 0, awayGoalsAgainst: 0,
    perCompetition: {}
  };
}

function bucket(): { matches: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number } {
  return { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
}

function tallyRecord(rec: TeamRecord, m: Match, side: 'home' | 'away'): void {
  if (m.homeGoal === null || m.awayGoal === null) return;
  const isHome = side === 'home';
  const myGoals = isHome ? m.homeGoal : m.awayGoal;
  const oppGoals = isHome ? m.awayGoal : m.homeGoal;
  let result: 'win' | 'draw' | 'loss';
  if (myGoals > oppGoals) result = 'win';
  else if (myGoals < oppGoals) result = 'loss';
  else result = 'draw';

  rec.matches++;
  rec.goalsFor += myGoals;
  rec.goalsAgainst += oppGoals;
  if (result === 'win') rec.wins++;
  else if (result === 'loss') rec.losses++;
  else rec.draws++;

  if (isHome) {
    rec.homeMatches++;
    rec.homeGoalsFor += myGoals;
    rec.homeGoalsAgainst += oppGoals;
    if (result === 'win') rec.homeWins++;
    else if (result === 'loss') rec.homeLosses++;
    else rec.homeDraws++;
  } else {
    rec.awayMatches++;
    rec.awayGoalsFor += myGoals;
    rec.awayGoalsAgainst += oppGoals;
    if (result === 'win') rec.awayWins++;
    else if (result === 'loss') rec.awayLosses++;
    else rec.awayDraws++;
  }

  const cb = rec.perCompetition[m.competition] ?? bucket();
  cb.matches++;
  cb.goalsFor += myGoals;
  cb.goalsAgainst += oppGoals;
  if (result === 'win') cb.wins++;
  else if (result === 'loss') cb.losses++;
  else cb.draws++;
  rec.perCompetition[m.competition] = cb;
}

export interface TeamQuery extends Omit<MatchQuery, 'team2' | 'asTeam'> {}

/**
 * Build a {@link TeamRecord} for `team` over all matches that match
 * the optional `query` filter.
 */
export function teamRecord(snap: DatasetSnapshot, team: string, query: TeamQuery = {}): TeamRecord {
  const rec = emptyRecord();
  const matches = findMatches(snap, { ...query, team, asTeam: 'either', includeUnknownScores: false });
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    if (teamMatches(m.homeTeam, team)) tallyRecord(rec, m, 'home');
    else if (teamMatches(m.awayTeam, team)) tallyRecord(rec, m, 'away');
  }
  return rec;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  matches: number;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  goalsFor1: number;
  goalsFor2: number;
  matchesByCompetition: Record<string, number>;
}

export function headToHead(snap: DatasetSnapshot, team1: string, team2: string, query: TeamQuery = {}): HeadToHead {
  const list = findMatches(snap, { ...query, team: team1, team2, includeUnknownScores: false });
  const out: HeadToHead = {
    team1: team1, team2, matches: 0, team1Wins: 0, team2Wins: 0, draws: 0,
    goalsFor1: 0, goalsFor2: 0, matchesByCompetition: {}
  };
  for (const m of list) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const t1IsHome = teamMatches(m.homeTeam, team1);
    out.matches++;
    out.goalsFor1 += t1IsHome ? m.homeGoal : m.awayGoal;
    out.goalsFor2 += t1IsHome ? m.awayGoal : m.homeGoal;
    if (m.homeGoal > m.awayGoal) {
      if (t1IsHome) out.team1Wins++; else out.team2Wins++;
    } else if (m.homeGoal < m.awayGoal) {
      if (t1IsHome) out.team2Wins++; else out.team1Wins++;
    } else {
      out.draws++;
    }
    out.matchesByCompetition[m.competition] = (out.matchesByCompetition[m.competition] ?? 0) + 1;
  }
  return out;
}

export interface StandingsRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

/**
 * Compute a round-robin table for the given season + competition.
 *
 * Win = 3 pts, draw = 1, loss = 0. If `competition` is omitted, all
 * Brasileirao-shaped competitions are pooled; callers usually want
 * just one source.
 */
export function standings(snap: DatasetSnapshot, season: number, competition?: Competition): StandingsRow[] {
  const matches = findMatches(snap, {
    season, competition: competition ?? ['brasileirao', 'brasileirao_historical'], includeUnknownScores: false
  });
  const table = new Map<string, StandingsRow>();
  const rowFor = (name: string): StandingsRow => {
    let r = table.get(name);
    if (!r) {
      r = {
        team: name, played: 0, wins: 0, draws: 0, losses: 0,
        goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0
      };
      table.set(name, r);
    }
    return r;
  };
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const home = rowFor(m.homeTeam);
    const away = rowFor(m.awayTeam);
    home.played++; away.played++;
    home.goalsFor += m.homeGoal; home.goalsAgainst += m.awayGoal;
    away.goalsFor += m.awayGoal; away.goalsAgainst += m.homeGoal;
    if (m.homeGoal > m.awayGoal) {
      home.wins++; home.points += 3; away.losses++;
    } else if (m.homeGoal < m.awayGoal) {
      away.wins++; away.points += 3; home.losses++;
    } else {
      home.draws++; away.draws++; home.points += 1; away.points += 1;
    }
  }
  for (const r of table.values()) r.goalDifference = r.goalsFor - r.goalsAgainst;
  return [...table.values()].sort((a, b) =>
    b.points - a.points ||
    b.wins - a.wins ||
    b.goalDifference - a.goalDifference ||
    b.goalsFor - a.goalsFor
  );
}
