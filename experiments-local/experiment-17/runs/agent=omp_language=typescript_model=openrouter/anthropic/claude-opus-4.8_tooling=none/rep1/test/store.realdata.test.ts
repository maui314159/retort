/**
 * Context
 * =======
 * Integration tests against the real bundled CSVs (data/kaggle/). These verify
 * the spec's data-coverage success criteria: all six files load, cross-file
 * queries work, dedupe enforces the one-fixture-per-season invariant, and at
 * least one well-known historical result (2019 Brasileirão = Flamengo, 90 pts —
 * the spec's own example) is reproduced exactly from computed standings.
 *
 * The store is loaded once and shared (loading ~17k matches + 18k players takes
 * well under the spec's 5s aggregate budget).
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { DataStore } from '../src/store.js';

let store: DataStore;

beforeAll(() => {
  store = DataStore.fromDataDir('data/kaggle');
});

describe('Feature: dataset loading and coverage', () => {
  it('Given the six CSVs, When loaded, Then matches and players are populated', () => {
    expect(store.matches.length).toBeGreaterThan(15000);
    expect(store.players.length).toBe(18207);
  });

  it('Given the data, When I list competitions, Then all expected competitions are present', () => {
    const comps = store.competitions();
    expect(comps).toContain('Brasileirão Série A');
    expect(comps).toContain('Copa do Brasil');
    expect(comps).toContain('Copa Libertadores');
  });

  it('Given overlapping sources, When deduped, Then a season has one row per ordered pair', () => {
    const m2019 = store.matches.filter(
      (m) => m.competition === 'Brasileirão Série A' && m.season === 2019,
    );
    // 20-team double round-robin = 380 matches exactly.
    expect(m2019).toHaveLength(380);
    const pairs = new Set(m2019.map((m) => `${m.canonicalHome}|${m.canonicalAway}`));
    expect(pairs.size).toBe(380);
  });
});

describe('Feature: historical standings (spec example)', () => {
  it('Given 2019, When standings are computed, Then Flamengo are champions with 90 points', () => {
    const rows = store.standings('Brasileirão', 2019);
    expect(rows).toHaveLength(20);
    expect(rows[0].team).toBe('Flamengo');
    expect(rows[0].points).toBe(90);
    expect(rows[0].played).toBe(38);
  });

  it('Given 2003 (44-game first division), When standings are computed, Then Cruzeiro are champions', () => {
    const rows = store.standings('Brasileirão', 2003);
    expect(rows[0].team).toBe('Cruzeiro');
  });
});

describe('Feature: cross-file queries (players + matches)', () => {
  it('Given a Brazilian club, When I list its FIFA roster, Then players resolve via shared canonical names', () => {
    // Grêmio appears as "Grêmio" in FIFA and "Grêmio-RS"/"Gremio" in match data.
    const roster = store.findPlayers({ club: 'Grêmio' });
    expect(roster.length).toBeGreaterThan(0);
    const record = store.teamRecord('Grêmio', { competition: 'Brasileirão' });
    expect(record.matches).toBeGreaterThan(0);
  });

  it('Given Brazilian players, When I search by nationality, Then top players are returned by rating', () => {
    const players = store.findPlayers({ nationality: 'Brazil', limit: 3 });
    expect(players).toHaveLength(3);
    expect(players[0].name).toBe('Neymar Jr');
    expect(players[0].overall).toBe(92);
  });
});

describe('Feature: head-to-head on real data (Fla-Flu derby)', () => {
  it('Given Flamengo and Fluminense, When compared, Then meetings and a consistent tally return', () => {
    const h = store.headToHead('Flamengo', 'Fluminense');
    expect(h.matches.length).toBeGreaterThan(10);
    expect(h.aWins + h.bWins + h.draws).toBe(h.matches.length);
  });
});

describe('Query performance', () => {
  it('Given the loaded store, When running an aggregate query, Then it completes well under budget', () => {
    const start = performance.now();
    store.standings('Brasileirão', 2019);
    store.leagueStats({ competition: 'Brasileirão' });
    store.findPlayers({ nationality: 'Brazil', limit: 50 });
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(2000);
  });
});
