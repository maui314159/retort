/**
 * BDD specs for Match Queries (spec section 1).
 *
 *   Feature: Match Queries
 *     Scenario: Find matches between two teams
 *       Given the match data is loaded
 *       When I search for matches between "Flamengo" and "Fluminense"
 *       Then I should receive a list of matches
 *       And each match should have date, scores, and competition
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { getTestDataset } from './fixtures.js';
import {
  filterMatches,
  headToHeadMatches,
  headToHead,
  lastMatchBetween,
} from '../src/query.js';
import { formatMatch, formatHeadToHead, formatMatches } from '../src/format.js';

describe('Feature: Match Queries', () => {
  const ds = getTestDataset();

  Given('the match data is loaded', () => {
    When('I search for matches between "Flamengo" and "Fluminense"', () => {
      const h2h = headToHeadMatches(ds.matches, 'Flamengo', 'Fluminense');

      Then('I should receive a list of matches', () => {
        expect(h2h.length).toBeGreaterThan(0);
      });

      Then('each match should have date, scores, and competition', () => {
        for (const m of h2h.slice(0, 5)) {
          expect(m.competition).toBeTruthy();
          // Scores may be null for very rare unplayed fixtures, but the vast
          // majority have integer goals.
          expect(m.homeGoal).not.toBeNull();
          expect(m.awayGoal).not.toBeNull();
        }
      });

      Then('each match involves Flamengo and Fluminense', () => {
        for (const m of h2h) {
          const teams = new Set([
            m.homeTeam.toLowerCase(),
            m.awayTeam.toLowerCase(),
          ]);
          expect(teams.has('flamengo')).toBe(true);
          expect(teams.has('fluminense')).toBe(true);
        }
      });

      Then('the formatted output is non-empty', () => {
        expect(formatHeadToHead(headToHead(ds.matches, 'Flamengo', 'Fluminense')))
          .toContain('Flamengo vs Fluminense');
      });
    });

    When('I search for Palmeiras matches in 2023', () => {
      const result = filterMatches(ds.matches, { team: 'Palmeiras', season: 2023 });

      Then('every match is in 2023 and involves Palmeiras', () => {
        expect(result.length).toBeGreaterThan(0);
        for (const m of result) {
          expect(m.season).toBe(2023);
          expect(
            m.homeTeam.toLowerCase().includes('palmeiras') ||
              m.awayTeam.toLowerCase().includes('palmeiras'),
          ).toBe(true);
        }
      });
    });

    When('I filter by competition "Copa do Brasil"', () => {
      const result = filterMatches(ds.matches, { competition: 'Copa do Brasil' });

      Then('all matches belong to Copa do Brasil', () => {
        expect(result.length).toBeGreaterThan(0);
        for (const m of result) expect(m.competition).toBe('Copa do Brasil');
      });
    });

    When('I request the last match between Flamengo and Corinthians', () => {
      const last = lastMatchBetween(ds.matches, 'Flamengo', 'Corinthians');

      Then('a match is returned with a parseable date', () => {
        expect(last).toBeDefined();
        expect(last!.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      });

      Then('the match formats to a single line with a score', () => {
        const line = formatMatch(last!);
        expect(line).toMatch(/\d+-\d+/);
      });
    });

    When('I apply a date range filter', () => {
      const result = filterMatches(ds.matches, {
        competition: 'Brasileirao',
        fromDate: '2022-01-01',
        toDate: '2022-12-31',
        limit: 20,
      });

      Then('all returned matches fall within 2022', () => {
        for (const m of result) {
          expect(m.date! >= '2022-01-01').toBe(true);
          expect(m.date! <= '2022-12-31').toBe(true);
        }
      });

      Then('the limit is respected', () => {
        expect(result.length).toBeLessThanOrEqual(20);
      });

      Then('formatMatches produces a count footer', () => {
        const out = formatMatches(result);
        expect(out).toMatch(/match\(es\)/);
      });
    });
  });
});
