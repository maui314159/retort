/**
 * Context
 * =======
 * BDD tests for the DataStore query engine against a small, fully-known fixture
 * (test/fixtures.ts). Exact expected numbers are derived by hand in the fixture
 * doc comment, so these assert real query behavior — standings points, W/D/L,
 * head-to-head tallies, filters, sorting — not incidental defaults.
 */

import { describe, it, expect } from 'vitest';
import { DataStore } from '../src/store.js';
import { FIXTURE_MATCHES, FIXTURE_PLAYERS } from './fixtures.js';

const store = new DataStore(FIXTURE_MATCHES, FIXTURE_PLAYERS);

describe('Feature: match search', () => {
  it('Given two teams, When I search for their matches, Then I get only their meetings, newest first', () => {
    const matches = store.findMatches({ team: 'Team A', opponent: 'Team C' });
    // A-C meetings: Série A home, Série A away, Copa do Brasil. (3)
    expect(matches).toHaveLength(3);
    expect(matches[0].date).toBe('2023-06-01'); // newest first
    for (const m of matches) {
      const teams = new Set([m.canonicalHome, m.canonicalAway]);
      expect(teams.has('team a')).toBe(true);
      expect(teams.has('team c')).toBe(true);
    }
  });

  it('Given a competition and season filter, When I search, Then only matching rows return', () => {
    const matches = store.findMatches({ team: 'Team A', competition: 'Brasileirão', season: 2023 });
    expect(matches).toHaveLength(4);
    expect(matches.every((m) => m.competition === 'Brasileirão Série A' && m.season === 2023)).toBe(true);
  });

  it('Given a venue filter, When I search home-only, Then only home matches return', () => {
    const matches = store.findMatches({ team: 'Team A', homeOnly: true, competition: 'Brasileirão', season: 2023 });
    expect(matches).toHaveLength(2);
    expect(matches.every((m) => m.canonicalHome === 'team a')).toBe(true);
  });

  it('Given a date range, When I search, Then only matches in range return', () => {
    const matches = store.findMatches({ dateFrom: '2023-04-15', dateTo: '2023-04-29' });
    expect(matches.map((m) => m.date).sort()).toEqual(['2023-04-15', '2023-04-22', '2023-04-29']);
  });

  it('Given a limit, When I search, Then the result is capped', () => {
    expect(store.findMatches({ limit: 2 })).toHaveLength(2);
  });
});

describe('Feature: team statistics', () => {
  it('Given a team and season, When I request its record, Then W/D/L and goals are correct', () => {
    const rec = store.teamRecord('Team A', { competition: 'Brasileirão', season: 2023 });
    expect(rec).toEqual({ matches: 4, wins: 2, draws: 1, losses: 1, goalsFor: 4, goalsAgainst: 3 });
  });

  it('Given a venue filter, When I request the record, Then only that venue is counted', () => {
    const home = store.teamRecord('Team A', { competition: 'Brasileirão', season: 2023, venue: 'home' });
    expect(home).toEqual({ matches: 2, wins: 1, draws: 1, losses: 0, goalsFor: 3, goalsAgainst: 1 });
  });
});

describe('Feature: head-to-head', () => {
  it('Given two teams, When I compare them, Then wins/draws/goals tally correctly', () => {
    const h = store.headToHead('Team A', 'Team B');
    // A vs B: 2023 home A win 2-0, 2023 away A win 1-0, 2022 A loss 0-5. => A 2W, B 1W, 0D
    expect(h.aWins).toBe(2);
    expect(h.bWins).toBe(1);
    expect(h.draws).toBe(0);
    expect(h.aGoals).toBe(3);
    expect(h.bGoals).toBe(5);
    expect(h.matches).toHaveLength(3);
  });

  it('Given a competition filter, When I compare, Then only that competition counts', () => {
    const h = store.headToHead('Team A', 'Team C', { competition: 'Copa do Brasil' });
    expect(h.matches).toHaveLength(1);
    expect(h.aWins).toBe(1);
  });
});

describe('Feature: standings computed from results', () => {
  it('Given a season, When I compute standings, Then points and order match the known outcomes', () => {
    const rows = store.standings('Brasileirão', 2023);
    expect(rows.map((r) => r.team)).toEqual(['Team A', 'Team C', 'Team B']);

    const a = rows[0];
    expect(a).toMatchObject({ points: 7, wins: 2, draws: 1, losses: 1, goalsFor: 4, goalsAgainst: 3, played: 4 });
    const c = rows[1];
    expect(c).toMatchObject({ points: 5, wins: 1, draws: 2, losses: 1 });
    const b = rows[2];
    expect(b).toMatchObject({ points: 4, wins: 1, draws: 1, losses: 2 });
  });

  it('Given an unknown competition, When I compute standings, Then it returns empty', () => {
    expect(store.standings('Nonexistent League', 2023)).toEqual([]);
  });
});

describe('Feature: aggregate statistics', () => {
  it('Given a competition+season, When I request league stats, Then goals and rates are correct', () => {
    const stats = store.leagueStats({ competition: 'Brasileirão', season: 2023 });
    // 6 Série A 2023 matches; goals: (2+0)+(0+1)+(1+1)+(2+0)+(3+1)+(2+2) = 15
    expect(stats.matches).toBe(6);
    expect(stats.totalGoals).toBe(15);
    expect(stats.avgGoalsPerMatch).toBeCloseTo(15 / 6, 5);
  });

  it('Given matches, When I request biggest wins, Then they are ordered by margin', () => {
    const wins = store.biggestWins({ limit: 2 });
    expect(Math.abs(wins[0].homeGoals - wins[0].awayGoals)).toBe(5); // 0-5 in 2022
    expect(Math.abs(wins[1].homeGoals - wins[1].awayGoals)).toBe(4); // 4-0 cup
  });
});

describe('Feature: player search', () => {
  it('Given a nationality, When I search, Then only that nationality returns, sorted by rating', () => {
    const players = store.findPlayers({ nationality: 'Brazil' });
    expect(players.map((p) => p.name)).toEqual(['Alpha Silva', 'Beta Souza']);
  });

  it('Given a club, When I search, Then players at that club return regardless of name spelling', () => {
    const players = store.findPlayers({ club: 'Team A' });
    expect(players.map((p) => p.id).sort()).toEqual([1, 3]);
  });

  it('Given a position and min rating, When I search, Then both filters apply', () => {
    const players = store.findPlayers({ position: 'ST', minOverall: 85 });
    expect(players).toHaveLength(1);
    expect(players[0].name).toBe('Alpha Silva');
  });

  it('Given a name substring, When I search, Then matching players return (accent-insensitive)', () => {
    expect(store.findPlayers({ name: 'alpha' }).map((p) => p.id)).toEqual([1]);
  });
});
