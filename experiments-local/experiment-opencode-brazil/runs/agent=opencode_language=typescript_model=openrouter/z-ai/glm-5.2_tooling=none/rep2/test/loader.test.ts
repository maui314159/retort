/**
 * BDD specs for the CSV loader: all six files load & normalize correctly.
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { loadDataset, resolveDataDir } from '../src/loader.js';
import { getTestDataset } from './fixtures.js';

describe('Loader', () => {
  Given('the data/kaggle directory', () => {
    When('the dataset is loaded', () => {
      Then('a Dataset is returned with matches and players', () => {
        const ds = loadDataset(resolveDataDir());
        expect(ds.matches.length).toBeGreaterThan(0);
        expect(ds.players.length).toBeGreaterThan(0);
      });

      Then('Brasileirao matches are present', () => {
        const ds = getTestDataset();
        const comp = ds.matches.filter((m) => m.competition === 'Brasileirao');
        expect(comp.length).toBeGreaterThan(1000);
      });

      Then('Copa do Brasil matches are present', () => {
        const ds = getTestDataset();
        const comp = ds.matches.filter((m) => m.competition === 'Copa do Brasil');
        expect(comp.length).toBeGreaterThan(500);
      });

      Then('Libertadores matches are present', () => {
        const ds = getTestDataset();
        const comp = ds.matches.filter((m) => m.competition === 'Libertadores');
        expect(comp.length).toBeGreaterThan(500);
      });

      Then('Historical Brasileirao matches are present', () => {
        const ds = getTestDataset();
        const comp = ds.matches.filter((m) => m.competition === 'Historical Brasileirao');
        expect(comp.length).toBeGreaterThan(1000);
      });

      Then('BR-Football extended-stats matches are present', () => {
        const ds = getTestDataset();
        const comp = ds.matches.filter((m) => m.competition === 'BR-Football');
        expect(comp.length).toBeGreaterThan(1000);
        expect(comp.some((m) => m.stats && m.stats.homeShots != null)).toBe(true);
      });

      Then('FIFA players are present with ratings', () => {
        const ds = getTestDataset();
        expect(ds.players.some((p) => p.overall != null && p.overall > 80)).toBe(true);
      });

      Then('team names have their state suffix stripped', () => {
        const ds = getTestDataset();
        const brasileirao = ds.matches.filter((m) => m.competition === 'Brasileirao');
        expect(brasileirao.some((m) => !m.homeTeam.includes('-'))).toBe(true);
      });
    });
  });
});
