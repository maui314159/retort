/**
 * BDD specs for Player Queries (spec section 3).
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { getTestDataset } from './fixtures.js';
import {
  searchPlayers,
  playersByNationality,
  playersByClub,
  topPlayers,
} from '../src/query.js';
import { formatPlayers } from '../src/format.js';

describe('Feature: Player Queries', () => {
  const ds = getTestDataset();

  Given('the FIFA player data is loaded', () => {
    When('I search for a player named "Neymar"', () => {
      const result = searchPlayers(ds.players, 'Neymar');

      Then('at least one Neymar record is returned', () => {
        expect(result.length).toBeGreaterThan(0);
        expect(result.some((p) => p.name.toLowerCase().includes('neymar'))).toBe(true);
      });
    });

    When('I filter by Brazilian nationality', () => {
      const brazilians = playersByNationality(ds.players, 'Brazil');

      Then('a large set of Brazilian players is returned', () => {
        expect(brazilians.length).toBeGreaterThan(100);
      });

      Then('top-rated Brazilians are sorted by overall desc', () => {
        const top = topPlayers(ds.players, { nationality: 'Brazil', limit: 5 });
        for (let i = 1; i < top.length; i++) {
          expect((top[i - 1].overall ?? 0) >= (top[i].overall ?? 0)).toBe(true);
        }
      });
    });

    When('I filter players by club "Flamengo"', () => {
      const flamengo = playersByClub(ds.players, 'Flamengo');

      Then('every returned player is at a Flamengo club', () => {
        for (const p of flamengo) {
          expect(p.club?.toLowerCase()).toContain('flamengo');
        }
      });
    });

    When('I request the top 10 players overall', () => {
      const top = topPlayers(ds.players, { limit: 10 });

      Then('10 players are returned in rating order', () => {
        expect(top.length).toBe(10);
        for (let i = 1; i < top.length; i++) {
          expect((top[i - 1].overall ?? 0) >= (top[i].overall ?? 0)).toBe(true);
        }
      });

      Then('the formatted output is numbered', () => {
        const out = formatPlayers(top, 'Top 10:');
        expect(out).toContain('1. ');
        expect(out).toContain('10. ');
      });
    });
  });
});
