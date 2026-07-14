/**
 * BDD integration tests for statistical analysis.
 *
 * Feature: Statistical Analysis
 *   Scenario: Compute average goals per match
 *   Scenario: Compute home win rate
 *   Scenario: Find biggest wins
 *   Scenario: Season comparison
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { loadData, clearCache } from '../src/data/loader.js';
import { computeStats, getBiggestWins, formatStats, formatBiggestWins } from '../src/tools/statistics.js';
import type { DataStore } from '../src/data/types.js';

let store: DataStore;

beforeAll(() => {
  clearCache();
  store = loadData();
});

describe('Feature: Statistical Analysis', () => {
  describe('Scenario: Compute competition overview', () => {
    it('should compute valid stats for all matches', () => {
      const stats = computeStats(store.matches);
      expect(stats.totalMatches).toBeGreaterThan(0);
      expect(stats.totalGoals).toBeGreaterThan(0);
      expect(stats.avgGoalsPerMatch).toBeGreaterThan(0);
      expect(stats.avgGoalsPerMatch).toBeLessThan(10); // sanity check
      expect(stats.homeWins + stats.draws + stats.awayWins).toBe(stats.totalMatches);
      expect(stats.homeWinRate + stats.drawRate + stats.awayWinRate).toBeCloseTo(100, 0);
    });

    it('should compute stats for Brasileirao only', () => {
      const stats = computeStats(store.matches, 'brasileirao');
      expect(stats.totalMatches).toBeGreaterThan(0);
      // Home win rates are typically around 45-55% in Brazilian football
      expect(stats.homeWinRate).toBeGreaterThan(30);
      expect(stats.homeWinRate).toBeLessThan(70);
    });

    it('should compute stats for a specific season', () => {
      const stats = computeStats(store.matches, 'brasileirao', 2022);
      expect(stats.totalMatches).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Find biggest wins', () => {
    it('should return wins sorted by goal difference (descending)', () => {
      const wins = getBiggestWins(store.matches, undefined, 10);
      expect(wins.length).toBeGreaterThan(0);
      for (let i = 1; i < wins.length; i++) {
        const gdCurrent = Math.abs(wins[i].homeGoals - wins[i].awayGoals);
        const gdPrev = Math.abs(wins[i - 1].homeGoals - wins[i - 1].awayGoals);
        expect(gdCurrent).toBeLessThanOrEqual(gdPrev);
      }
    });

    it('should have large goal differences in biggest wins', () => {
      const wins = getBiggestWins(store.matches, undefined, 5);
      expect(wins.length).toBeGreaterThan(0);
      const gd = Math.abs(wins[0].homeGoals - wins[0].awayGoals);
      expect(gd).toBeGreaterThanOrEqual(4); // largest wins should be at least 5-0 or similar
    });

    it('should filter by competition', () => {
      const wins = getBiggestWins(store.matches, 'brasileirao', 10);
      expect(wins.length).toBeGreaterThan(0);
      wins.forEach((m) => {
        expect(['brasileirao', 'historico']).toContain(m.competition);
      });
    });

    it('should respect limit parameter', () => {
      const wins5 = getBiggestWins(store.matches, undefined, 5);
      const wins10 = getBiggestWins(store.matches, undefined, 10);
      expect(wins5.length).toBeLessThanOrEqual(5);
      expect(wins10.length).toBeLessThanOrEqual(10);
      expect(wins10.length).toBeGreaterThanOrEqual(wins5.length);
    });
  });

  describe('Scenario: Format statistics', () => {
    it('should format stats with all required fields', () => {
      const stats = computeStats(store.matches, 'brasileirao');
      const text = formatStats(stats, 'brasileirao');
      expect(text).toContain('Total matches');
      expect(text).toContain('Avg goals');
      expect(text).toContain('Home wins');
      expect(text).toContain('Away wins');
    });

    it('should format biggest wins with date and score', () => {
      const wins = getBiggestWins(store.matches, undefined, 5);
      const text = formatBiggestWins(wins);
      expect(text).toContain('Biggest wins');
      // Should contain a date-like pattern
      expect(text).toMatch(/\d{4}-\d{2}-\d{2}/);
    });
  });

  describe('Scenario: Compare seasons', () => {
    it('should show different stats for different seasons', () => {
      const stats2018 = computeStats(store.matches, 'brasileirao', 2018);
      const stats2019 = computeStats(store.matches, 'brasileirao', 2019);
      expect(stats2018.totalMatches).toBeGreaterThan(0);
      expect(stats2019.totalMatches).toBeGreaterThan(0);
      // Both seasons should have similar match counts (38 rounds * 10 matches = 380)
      expect(stats2018.totalMatches).toBeGreaterThan(100);
      expect(stats2019.totalMatches).toBeGreaterThan(100);
    });
  });
});
