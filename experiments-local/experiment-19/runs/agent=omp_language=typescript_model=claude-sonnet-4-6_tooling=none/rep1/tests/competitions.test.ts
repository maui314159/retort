/**
 * BDD integration tests for competition standings.
 *
 * Feature: Competition Queries
 *   Scenario: Calculate Brasileirao standings for a season
 *   Scenario: Calculate Libertadores standings
 *   Scenario: Verify champion of a known season
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { loadData, clearCache } from '../src/data/loader.js';
import { getStandings, formatStandings, getAvailableSeasons } from '../src/tools/competitions.js';
import type { DataStore } from '../src/data/types.js';

let store: DataStore;

beforeAll(() => {
  clearCache();
  store = loadData();
});

describe('Feature: Competition Queries', () => {
  describe('Scenario: Get available seasons', () => {
    it('should list seasons for Brasileirao', () => {
      const seasons = getAvailableSeasons(store.matches, 'brasileirao');
      expect(seasons.length).toBeGreaterThan(0);
      // All seasons should be positive integers
      seasons.forEach((s) => expect(s).toBeGreaterThan(2000));
      // Seasons should be sorted ascending
      for (let i = 1; i < seasons.length; i++) {
        expect(seasons[i]).toBeGreaterThan(seasons[i - 1]);
      }
    });

    it('should list seasons for Libertadores', () => {
      const seasons = getAvailableSeasons(store.matches, 'libertadores');
      expect(seasons.length).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Calculate Brasileirao standings', () => {
    it('should produce standings for 2019 Brasileirao', () => {
      const standings = getStandings(store.matches, 'brasileirao', 2019);
      expect(standings.length).toBeGreaterThan(10);
      // Points should be non-increasing
      for (let i = 1; i < standings.length; i++) {
        expect(standings[i].points).toBeLessThanOrEqual(standings[i - 1].points);
      }
    });

    it('should have Flamengo at the top for 2019', () => {
      // Flamengo won the 2019 Brasileirao with a record-breaking campaign
      const standings = getStandings(store.matches, 'brasileirao', 2019);
      expect(standings.length).toBeGreaterThan(0);
      expect(standings[0].team.toLowerCase()).toContain('flamengo');
    });

    it('should produce valid standings structure', () => {
      const standings = getStandings(store.matches, 'brasileirao', 2022);
      expect(standings.length).toBeGreaterThan(0);
      for (const s of standings) {
        expect(s.played).toBeGreaterThan(0);
        expect(s.wins + s.draws + s.losses).toBe(s.played);
        expect(s.points).toBe(s.wins * 3 + s.draws);
        expect(s.goalsFor).toBeGreaterThanOrEqual(0);
        expect(s.goalsAgainst).toBeGreaterThanOrEqual(0);
      }
    });

    it('should produce historical standings for 2006', () => {
      const standings = getStandings(store.matches, 'brasileirao', 2006);
      expect(standings.length).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Format standings', () => {
    it('should format standings table', () => {
      const standings = getStandings(store.matches, 'brasileirao', 2019);
      const text = formatStandings(standings, 'brasileirao', 2019);
      expect(text).toContain('2019');
      expect(text).toContain('Flamengo');
      expect(text).toContain('Pts');
      expect(text).toContain('Champion');
    });

    it('should show no data message for invalid season', () => {
      const standings = getStandings(store.matches, 'brasileirao', 1900);
      const text = formatStandings(standings, 'brasileirao', 1900);
      expect(text).toContain('No match data found');
    });
  });

  describe('Scenario: Copa do Brasil standings', () => {
    it('should produce Copa do Brasil data for available seasons', () => {
      const seasons = getAvailableSeasons(store.matches, 'copa_do_brasil');
      expect(seasons.length).toBeGreaterThan(0);
    });
  });
});
