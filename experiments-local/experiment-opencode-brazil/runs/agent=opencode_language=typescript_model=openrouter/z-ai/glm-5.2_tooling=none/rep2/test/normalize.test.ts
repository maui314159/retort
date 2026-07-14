/**
 * BDD specs for name & date normalization.
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import {
  normalizeTeamName,
  normalizeKey,
  parseDate,
  parseGoals,
  parseSeason,
  stripStateSuffix,
  teamMatches,
  teamsEqual,
} from '../src/normalize.js';

describe('Normalization', () => {
  Given('team names with state suffixes', () => {
    When('the suffix is stripped', () => {
      Then('"Palmeiras-SP" becomes "Palmeiras"', () => {
        expect(stripStateSuffix('Palmeiras-SP')).toBe('Palmeiras');
      });
      Then('"Flamengo-RJ" is normalized to "Flamengo"', () => {
        expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
      });
    });
  });

  Given('accented team names', () => {
    When('compared via the normalize key', () => {
      Then('"São Paulo" equals "sao paulo"', () => {
        expect(teamsEqual('São Paulo', 'Sao Paulo')).toBe(true);
      });
      Then('"Grêmio" equals "Gremio"', () => {
        expect(teamsEqual('Grêmio', 'Gremio')).toBe(true);
      });
    });
  });

  Given('a substring team match query', () => {
    When('the canonical name is a substring', () => {
      Then('"Corinthians" matches "Sport Club Corinthians Paulista"', () => {
        expect(teamMatches('Sport Club Corinthians Paulista', 'Corinthians')).toBe(true);
      });
    });
  });

  Given('multiple date formats', () => {
    When('dates are parsed', () => {
      Then('ISO "2023-09-24 18:30:00" yields "2023-09-24"', () => {
        expect(parseDate('2023-09-24 18:30:00')).toBe('2023-09-24');
      });
      Then('Brazilian "29/03/2003" yields "2003-03-29"', () => {
        expect(parseDate('29/03/2003')).toBe('2003-03-29');
      });
      Then('plain ISO "2012-05-19" is preserved', () => {
        expect(parseDate('2012-05-19')).toBe('2012-05-19');
      });
    });
  });

  Given('goal & season values of varying types', () => {
    When('parsed', () => {
      Then('"2" parses to 2', () => expect(parseGoals('2')).toBe(2));
      Then('"2.0" parses to 2', () => expect(parseGoals('2.0')).toBe(2));
      Then('empty parses to null', () => expect(parseGoals('')).toBeNull());
      Then('"2023" season parses to 2023', () =>
        expect(parseSeason('2023')).toBe(2023));
    });
  });

  Given('the normalize key function', () => {
    Then('it folds accents and casing consistently', () => {
      expect(normalizeKey('Avaí')).toBe(normalizeKey('Avai'));
    });
  });
});
