/**
 * BDD integration tests for team statistics.
 *
 * Feature: Team Queries
 *   Scenario: Get team win/loss/draw record
 *   Scenario: Get home-only record
 *   Scenario: Get top scoring teams
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { loadData, clearCache } from '../src/data/loader.js';
import { getTeamRecord, getTopGoalTeams, formatTeamStats } from '../src/tools/teams.js';
import type { DataStore } from '../src/data/types.js';

let store: DataStore;

beforeAll(() => {
  clearCache();
  store = loadData();
});

describe('Feature: Team Queries', () => {
  describe('Scenario: Get team overall record', () => {
    it('should return a valid record for Flamengo', () => {
      const record = getTeamRecord(store.matches, 'Flamengo');
      expect(record.played).toBeGreaterThan(0);
      expect(record.wins + record.draws + record.losses).toBe(record.played);
      expect(record.points).toBe(record.wins * 3 + record.draws);
    });

    it('should return a valid record for Palmeiras', () => {
      const record = getTeamRecord(store.matches, 'Palmeiras');
      expect(record.played).toBeGreaterThan(0);
      expect(record.goalsFor).toBeGreaterThan(0);
    });

    it('should return zero played for a non-existent team', () => {
      const record = getTeamRecord(store.matches, 'NonExistentTeamXYZ123');
      expect(record.played).toBe(0);
    });
  });

  describe('Scenario: Get team record filtered by season', () => {
    it('should return season-specific stats for Corinthians 2019 across all competitions', () => {
      const record = getTeamRecord(store.matches, 'Corinthians', undefined, 2019);
      expect(record.played).toBeGreaterThan(0);
      // Multiple datasets (brasileirao, copa, extended, historico) each contribute matches;
      // total can exceed 100 for a popular club across all competitions in one year
      expect(record.played).toBeLessThanOrEqual(200);
    });
  });

  describe('Scenario: Get team home record', () => {
    it('should return home-only record', () => {
      const homeRecord = getTeamRecord(store.matches, 'Flamengo', undefined, undefined, true, false);
      const awayRecord = getTeamRecord(store.matches, 'Flamengo', undefined, undefined, false, true);
      const allRecord = getTeamRecord(store.matches, 'Flamengo');

      expect(homeRecord.played + awayRecord.played).toBeLessThanOrEqual(allRecord.played + 2); // near equal
      expect(homeRecord.played).toBeGreaterThan(0);
      expect(awayRecord.played).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Get team record by competition', () => {
    it('should return Flamengo stats in Brasileirao only', () => {
      const record = getTeamRecord(store.matches, 'Flamengo', 'brasileirao');
      expect(record.played).toBeGreaterThan(0);
    });

    it('should return Flamengo stats in Libertadores', () => {
      const record = getTeamRecord(store.matches, 'Flamengo', 'libertadores');
      expect(record.played).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Format team stats', () => {
    it('should format stats correctly', () => {
      const record = getTeamRecord(store.matches, 'Palmeiras', 'brasileirao', 2022);
      const text = formatTeamStats(record, 'brasileirao', 2022);
      expect(text).toContain('Palmeiras');
      expect(text).toContain('Wins');
      expect(text).toContain('Goals For');
      expect(text).toContain('Win Rate');
    });

    it('should handle zero matches gracefully', () => {
      const record = getTeamRecord(store.matches, 'NonExistentTeamXYZ', 'brasileirao', 2022);
      const text = formatTeamStats(record, 'brasileirao', 2022);
      expect(text).toContain('No matches found');
    });
  });

  describe('Scenario: Top scoring teams', () => {
    it('should return top scoring teams for Brasileirao', () => {
      const top = getTopGoalTeams(store.matches, 'brasileirao', undefined, 10);
      expect(top.length).toBeGreaterThan(0);
      expect(top.length).toBeLessThanOrEqual(10);
      // Should be sorted descending by goals
      for (let i = 1; i < top.length; i++) {
        expect(top[i].goals).toBeLessThanOrEqual(top[i - 1].goals);
      }
    });

    it('should return top scoring teams for a specific season', () => {
      const top = getTopGoalTeams(store.matches, 'brasileirao', 2019, 5);
      expect(top.length).toBeGreaterThan(0);
      expect(top.length).toBeLessThanOrEqual(5);
    });
  });
});
