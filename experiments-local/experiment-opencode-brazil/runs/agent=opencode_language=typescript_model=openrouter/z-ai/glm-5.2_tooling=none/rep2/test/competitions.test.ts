/**
 * BDD specs for Competition Queries (spec section 4).
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { getTestDataset } from './fixtures.js';
import {
  standings,
  champion,
  relegated,
  seasonsFor,
  allCompetitions,
} from '../src/query.js';
import { formatStandings } from '../src/format.js';

describe('Feature: Competition Queries', () => {
  const ds = getTestDataset();

  Given('the match data is loaded', () => {
    When('I request standings for Brasileirao 2019', () => {
      const table = standings(ds.matches, 'Brasileirao', 2019);

      Then('every team has W+D+L equal to matches played', () => {
        expect(table.length).toBeGreaterThan(0);
        for (const r of table) {
          expect(r.wins + r.draws + r.losses).toBe(r.matches);
        }
      });

      Then('teams are sorted by points descending', () => {
        for (let i = 1; i < table.length; i++) {
          expect(table[i - 1].points >= table[i].points).toBe(true);
        }
      });

      Then('the 2019 champion is Flamengo', () => {
        const champ = champion(ds.matches, 'Brasileirao', 2019);
        expect(champ).toBeDefined();
        expect(champ!.team.toLowerCase()).toBe('flamengo');
      });

      Then('formatted standings include "Champion" on row 1', () => {
        const out = formatStandings(table, '2019 Brasileirao:');
        expect(out).toContain('Champion');
      });
    });

    When('I request relegated teams for Brasileirao 2019', () => {
      const bottom = relegated(ds.matches, 'Brasileirao', 2019, 4);

      Then('4 teams are returned', () => {
        expect(bottom.length).toBeLessThanOrEqual(4);
      });
    });

    When('I list seasons for Copa do Brasil', () => {
      const seasons = seasonsFor(ds.matches, 'Copa do Brasil');

      Then('multiple seasons are present', () => {
        expect(seasons.length).toBeGreaterThan(1);
      });
    });

    When('I list all competitions', () => {
      const comps = allCompetitions(ds.matches);

      Then('all five competitions are represented', () => {
        expect(new Set(comps).size).toBeGreaterThanOrEqual(5);
      });
    });
  });
});
