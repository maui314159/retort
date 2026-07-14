import { afterEach, describe, expect, it } from 'vitest';
import { getDatabase, resetDatabase } from '../data-loader.js';
import type { Match } from '../types.js';

afterEach(() => {
  resetDatabase();
});

describe('getDatabase', () => {
  it('loads all matches from all CSV files', () => {
    const { matches } = getDatabase();
    // 4180 + 1337 + 1255 + 10296 + 6886 = 23954, allow some variance for bad rows
    expect(matches.length).toBeGreaterThan(20000);
  });

  it('loads FIFA player data', () => {
    const { players } = getDatabase();
    expect(players.length).toBeGreaterThan(15000);
  });

  it('returns cached instance on repeated calls', () => {
    const db1 = getDatabase();
    const db2 = getDatabase();
    expect(db1).toBe(db2);
  });

  it('loads Brasileirão matches with correct fields', () => {
    const { matches } = getDatabase();
    const brasMatches = matches.filter((m) => m.source === 'brasileirao');
    expect(brasMatches.length).toBeGreaterThan(4000);

    const sample = brasMatches[0]!;
    expect(sample.homeTeam).toBeTruthy();
    expect(sample.awayTeam).toBeTruthy();
    expect(sample.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(sample.season).toBeGreaterThanOrEqual(2012);
    expect(sample.competition).toBe('Brasileirão Serie A');
    expect(typeof sample.homeGoals).toBe('number');
    expect(typeof sample.awayGoals).toBe('number');
  });

  it('loads Copa do Brasil matches', () => {
    const { matches } = getDatabase();
    const copaBrasil = matches.filter((m) => m.source === 'copa_brasil');
    expect(copaBrasil.length).toBeGreaterThan(1000);
    expect(copaBrasil[0]!.competition).toBe('Copa do Brasil');
  });

  it('loads Copa Libertadores matches', () => {
    const { matches } = getDatabase();
    const lib = matches.filter((m) => m.source === 'libertadores');
    expect(lib.length).toBeGreaterThan(1000);
    expect(lib[0]!.competition).toBe('Copa Libertadores');
  });

  it('loads historic Brasileirão matches with correct date parsing', () => {
    const { matches } = getDatabase();
    const hist = matches.filter((m) => m.source === 'historico');
    expect(hist.length).toBeGreaterThan(6000);

    const sample2003 = hist.find((m) => m.season === 2003);
    expect(sample2003).toBeDefined();
    expect(sample2003!.date).toMatch(/^2003-/);
  });

  it('loads BR-Football-Dataset with numeric goals', () => {
    const { matches } = getDatabase();
    const brMatches = matches.filter((m) => m.source === 'br_football');
    expect(brMatches.length).toBeGreaterThan(5000);

    // All goals should be integers
    for (const m of brMatches.slice(0, 100)) {
      expect(Number.isInteger(m.homeGoals)).toBe(true);
      expect(Number.isInteger(m.awayGoals)).toBe(true);
    }
  });

  it('normalizes team names by stripping state suffixes', () => {
    const { matches } = getDatabase();
    const brasMatches = matches.filter((m) => m.source === 'brasileirao');

    const palmeiras = brasMatches.find((m) => m.homeTeam === 'Palmeiras-SP');
    expect(palmeiras).toBeDefined();
    expect(palmeiras!.homeTeamNormalized).toBe('Palmeiras');
  });

  it('loads player nationality field', () => {
    const { players } = getDatabase();
    const brazilians = players.filter((p) => p.nationality === 'Brazil');
    expect(brazilians.length).toBeGreaterThan(500);
  });

  it('loads player overall rating', () => {
    const { players } = getDatabase();
    const topRated = players.filter((p) => (p.overall ?? 0) >= 90);
    expect(topRated.length).toBeGreaterThan(0);
  });
});

describe('resetDatabase', () => {
  it('forces reload on next getDatabase call', () => {
    const db1 = getDatabase();
    resetDatabase();
    const db2 = getDatabase();
    // New object reference after reset
    expect(db1).not.toBe(db2);
    // But same content
    expect(db2.matches.length).toBe(db1.matches.length);
  });
});
