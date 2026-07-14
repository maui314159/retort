/**
 * BDD specs for Team Queries (spec section 2).
 *
 *   Scenario: Get team statistics
 *     Given the match data is loaded
 *     When I request statistics for "Palmeiras" in season "2023"
 *     Then I should receive wins, losses, draws, and goals
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { getTestDataset } from './fixtures.js';
import {
  filterMatches,
  teamRecord,
  teamVenueRecord,
  allTeams,
} from '../src/query.js';
import { formatTeamRecord } from '../src/format.js';

describe('Feature: Team Queries', () => {
  const ds = getTestDataset();

  Given('the match data is loaded', () => {
    When('I request statistics for "Palmeiras" in season 2023', () => {
      const scoped = filterMatches(ds.matches, { team: 'Palmeiras', season: 2023 });
      const rec = teamRecord(scoped, 'Palmeiras');

      Then('I should receive wins, losses, draws, and goals', () => {
        expect(rec.matches).toBeGreaterThan(0);
        expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
        expect(rec.goalsFor).toBeGreaterThanOrEqual(0);
        expect(rec.goalsAgainst).toBeGreaterThanOrEqual(0);
        expect(rec.points).toBe(rec.wins * 3 + rec.draws);
      });

      Then('the formatted record includes a win rate', () => {
        const out = formatTeamRecord(rec, 'Palmeiras 2023:');
        expect(out).toContain('Win rate:');
        expect(out).toContain('%');
      });
    });

    When("I request Corinthians' home record in 2022", () => {
      const scoped = filterMatches(ds.matches, {
        team: 'Corinthians',
        season: 2022,
        competition: 'Brasileirao',
      });
      const home = teamVenueRecord(scoped, 'Corinthians', 'home');

      Then('home matches are counted (each as a home fixture)', () => {
        expect(home.matches).toBeGreaterThan(0);
        expect(home.matches).toBeLessThanOrEqual(scoped.length);
      });
    });

    When('I list all teams', () => {
      const teams = allTeams(ds.matches);

      Then('well-known Brazilian clubs appear', () => {
        const lower = teams.map((t) => t.toLowerCase());
        expect(lower).toContain('flamengo');
        expect(lower).toContain('palmeiras');
      });
    });
  });
});
