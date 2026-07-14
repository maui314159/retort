/**
 * BDD integration tests for match queries.
 *
 * Feature: Match Queries
 *   Scenario: Find matches between two teams
 *   Scenario: Find matches for a team in a season
 *   Scenario: Filter matches by competition
 *   Scenario: Head-to-head records
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { loadData, clearCache } from '../src/data/loader.js';
import { searchMatches, getHeadToHead, formatHeadToHead } from '../src/tools/matches.js';
import type { DataStore } from '../src/data/types.js';

let store: DataStore;

beforeAll(() => {
  clearCache();
  store = loadData();
});

describe('Feature: Match Queries', () => {
  describe('Given the match data is loaded', () => {
    it('should have matches from all datasets', () => {
      expect(store.matches.length).toBeGreaterThan(1000);
    });

    it('should have matches from all competitions', () => {
      const competitions = new Set(store.matches.map((m) => m.competition));
      expect(competitions.has('brasileirao')).toBe(true);
      expect(competitions.has('copa_do_brasil')).toBe(true);
      expect(competitions.has('libertadores')).toBe(true);
      expect(competitions.has('historico')).toBe(true);
    });
  });

  describe('Scenario: Find matches for a single team', () => {
    it('should find Flamengo matches', () => {
      const results = searchMatches(store.matches, { team: 'Flamengo', limit: 50 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((m) => {
        const hasFlamengo =
          m.homeTeam.toLowerCase().includes('flamengo') ||
          m.awayTeam.toLowerCase().includes('flamengo');
        expect(hasFlamengo).toBe(true);
      });
    });

    it('should find Palmeiras matches (with state suffix in data)', () => {
      const results = searchMatches(store.matches, { team: 'Palmeiras', limit: 50 });
      expect(results.length).toBeGreaterThan(0);
    });

    it('should return results sorted by date descending', () => {
      const results = searchMatches(store.matches, { team: 'Corinthians', limit: 10 });
      for (let i = 1; i < results.length; i++) {
        expect(results[i].date <= results[i - 1].date).toBe(true);
      }
    });
  });

  describe('Scenario: Filter matches by season', () => {
    it('should return only matches from the specified season', () => {
      const results = searchMatches(store.matches, { team: 'Flamengo', season: 2019, limit: 50 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((m) => {
        expect(m.season).toBe(2019);
      });
    });
  });

  describe('Scenario: Filter matches by competition', () => {
    it('should return only Brasileirao matches', () => {
      const results = searchMatches(store.matches, { competition: 'brasileirao', limit: 20 });
      expect(results.length).toBe(20);
      results.forEach((m) => {
        expect(['brasileirao', 'historico']).toContain(m.competition);
      });
    });

    it('should return only Libertadores matches', () => {
      const results = searchMatches(store.matches, { competition: 'libertadores', limit: 20 });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((m) => {
        expect(m.competition).toBe('libertadores');
      });
    });
  });

  describe('Scenario: Filter by date range', () => {
    it('should return matches within date range', () => {
      const results = searchMatches(store.matches, {
        dateFrom: '2023-01-01',
        dateTo: '2023-12-31',
        limit: 50,
      });
      results.forEach((m) => {
        expect(m.date >= '2023-01-01').toBe(true);
        expect(m.date <= '2023-12-31').toBe(true);
      });
    });
  });

  describe('Scenario: Head-to-head between two teams', () => {
    it('should find Flamengo vs Fluminense matches', () => {
      const result = getHeadToHead(store.matches, 'Flamengo', 'Fluminense');
      expect(result.matches.length).toBeGreaterThan(0);
      result.matches.forEach((m) => {
        const hasFlamengo = m.homeTeam.toLowerCase().includes('flamengo') || m.awayTeam.toLowerCase().includes('flamengo');
        const hasFluminense = m.homeTeam.toLowerCase().includes('fluminense') || m.awayTeam.toLowerCase().includes('fluminense');
        expect(hasFlamengo && hasFluminense).toBe(true);
      });
    });

    it('should correctly count wins/draws/losses', () => {
      const result = getHeadToHead(store.matches, 'Flamengo', 'Fluminense');
      expect(result.team1Wins + result.team2Wins + result.draws).toBe(result.matches.length);
    });

    it('should format head-to-head output', () => {
      const result = getHeadToHead(store.matches, 'Palmeiras', 'Santos');
      const text = formatHeadToHead(result, 'Palmeiras', 'Santos');
      expect(text).toContain('Palmeiras');
      expect(text).toContain('Santos');
      expect(text).toContain('Head-to-head');
    });

    it('should find Corinthians vs Palmeiras matches', () => {
      const result = getHeadToHead(store.matches, 'Corinthians', 'Palmeiras');
      expect(result.matches.length).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Find matches between two specific teams (team1+team2)', () => {
    it('should only return matches where both teams played', () => {
      const results = searchMatches(store.matches, {
        team1: 'Flamengo',
        team2: 'Vasco',
        limit: 20,
      });
      expect(results.length).toBeGreaterThan(0);
      results.forEach((m) => {
        const hasFlamengo = m.homeTeam.toLowerCase().includes('flamengo') || m.awayTeam.toLowerCase().includes('flamengo');
        const hasVasco = m.homeTeam.toLowerCase().includes('vasco') || m.awayTeam.toLowerCase().includes('vasco');
        expect(hasFlamengo && hasVasco).toBe(true);
      });
    });
  });
});
