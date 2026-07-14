/**
 * BDD specs for Statistical Analysis (spec section 5).
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { getTestDataset } from './fixtures.js';
import {
  averageGoalsPerMatch,
  homeAwayRates,
  biggestWins,
  filterMatches,
} from '../src/query.js';
import { formatStats } from '../src/format.js';

describe('Feature: Statistical Analysis', () => {
  const ds = getTestDataset();

  Given('the match data is loaded', () => {
    When('I compute the average goals per Brasileirao match', () => {
      const scoped = filterMatches(ds.matches, { competition: 'Brasileirao' });
      const avg = averageGoalsPerMatch(scoped);

      Then('the average is a sensible positive number', () => {
        expect(avg).toBeGreaterThan(1);
        expect(avg).toBeLessThan(6);
      });
    });

    When('I compute home/away win rates', () => {
      const scoped = filterMatches(ds.matches, { competition: 'Brasileirao' });
      const rates = homeAwayRates(scoped);

      Then('home + draw + away rates sum to ~1.0', () => {
        const sum = rates.homeWinRate + rates.drawRate + rates.awayWinRate;
        expect(Math.abs(sum - 1)).toBeLessThan(1e-6);
      });

      Then('home win rate exceeds away win rate (home advantage)', () => {
        expect(rates.homeWinRate).toBeGreaterThan(rates.awayWinRate);
      });

      Then('formatStats reports all three rates', () => {
        const out = formatStats(scoped);
        expect(out).toContain('Home win rate:');
        expect(out).toContain('Away win rate:');
      });
    });

    When('I look for the biggest wins', () => {
      const wins = biggestWins(ds.matches, 5);

      Then('matches are ordered by decreasing goal difference', () => {
        for (let i = 1; i < wins.length; i++) {
          const a = Math.abs(wins[i - 1].homeGoal! - wins[i - 1].awayGoal!);
          const b = Math.abs(wins[i].homeGoal! - wins[i].awayGoal!);
          expect(a >= b).toBe(true);
        }
      });
    });
  });
});
