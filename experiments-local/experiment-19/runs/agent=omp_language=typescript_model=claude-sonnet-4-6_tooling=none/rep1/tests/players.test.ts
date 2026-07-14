/**
 * BDD integration tests for player queries.
 *
 * Feature: Player Queries
 *   Scenario: Search players by name
 *   Scenario: Filter players by nationality
 *   Scenario: Filter players by club
 *   Scenario: Filter by position and rating
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { loadData, clearCache } from '../src/data/loader.js';
import { searchPlayers, formatPlayerResults } from '../src/tools/players.js';
import type { DataStore } from '../src/data/types.js';

let store: DataStore;

beforeAll(() => {
  clearCache();
  store = loadData();
});

describe('Feature: Player Queries', () => {
  describe('Given the FIFA player data is loaded', () => {
    it('should have a large player database', () => {
      expect(store.players.length).toBeGreaterThan(1000);
    });
  });

  describe('Scenario: Search player by name', () => {
    it('should find Neymar Jr', () => {
      const results = searchPlayers(store.players, { name: 'Neymar' });
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].name.toLowerCase()).toContain('neymar');
    });

    it('should find Gabriel Barbosa (Gabigol)', () => {
      const results = searchPlayers(store.players, { name: 'Gabriel' });
      expect(results.length).toBeGreaterThan(0);
    });

    it('should return empty for non-existent player', () => {
      const results = searchPlayers(store.players, { name: 'ZZZNonExistentPlayerXXX' });
      expect(results.length).toBe(0);
    });
  });

  describe('Scenario: Filter players by nationality', () => {
    it('should find Brazilian players', () => {
      const results = searchPlayers(store.players, { nationality: 'Brazil', limit: 50 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((p) => {
        expect(p.nationality).toBe('Brazil');
      });
    });

    it('should sort Brazilian players by overall rating', () => {
      const results = searchPlayers(store.players, { nationality: 'Brazil', limit: 10 });
      for (let i = 1; i < results.length; i++) {
        expect(results[i].overall).toBeLessThanOrEqual(results[i - 1].overall);
      }
      // Top Brazilian player should be Neymar or similar high-rated player
      expect(results[0].overall).toBeGreaterThanOrEqual(85);
    });
  });

  describe('Scenario: Filter players by club', () => {
    it('should find players at Fluminense (present in FIFA 19 dataset)', () => {
      const results = searchPlayers(store.players, { club: 'Fluminense', limit: 20 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((p) => {
        expect(p.club.toLowerCase()).toContain('fluminense');
      });
    });
  });

  describe('Scenario: Filter by position', () => {
    it('should find goalkeepers', () => {
      const results = searchPlayers(store.players, { position: 'GK', limit: 10 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((p) => {
        expect(p.position).toContain('GK');
      });
    });

    it('should find strikers (ST)', () => {
      const results = searchPlayers(store.players, { position: 'ST', limit: 10 });
      expect(results.length).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Filter by overall rating', () => {
    it('should return only players with rating >= 85', () => {
      const results = searchPlayers(store.players, { minOverall: 85, limit: 20 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((p) => {
        expect(p.overall).toBeGreaterThanOrEqual(85);
      });
    });

    it('should combine nationality and rating filters', () => {
      const results = searchPlayers(store.players, { nationality: 'Brazil', minOverall: 80, limit: 20 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((p) => {
        expect(p.nationality).toBe('Brazil');
        expect(p.overall).toBeGreaterThanOrEqual(80);
      });
    });
  });

  describe('Scenario: Format player results', () => {
    it('should format player list correctly', () => {
      const results = searchPlayers(store.players, { nationality: 'Brazil', limit: 5 });
      const text = formatPlayerResults(results, results.length, { nationality: 'Brazil', limit: 5 });
      expect(text).toContain('Players');
      expect(text).toContain('Brazil');
      expect(text).toContain('Overall');
    });

    it('should show "No players found" for empty results', () => {
      const text = formatPlayerResults([], 0, { name: 'XYZ' });
      expect(text).toContain('No players found');
    });
  });
});
