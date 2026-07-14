import { describe, expect, it } from 'vitest';
import { normalizeForSearch, parseDate, parseGoals, stripStateSuffix, teamMatches } from '../normalize.js';

describe('stripStateSuffix', () => {
  it('removes 2-letter state code after hyphen', () => {
    expect(stripStateSuffix('Palmeiras-SP')).toBe('Palmeiras');
    expect(stripStateSuffix('Flamengo-RJ')).toBe('Flamengo');
    expect(stripStateSuffix('Atletico-MG')).toBe('Atletico');
  });

  it('removes state code with space before hyphen', () => {
    expect(stripStateSuffix('América - MG')).toBe('América');
    expect(stripStateSuffix('Boavista - RJ')).toBe('Boavista');
  });

  it('leaves 3-letter country codes intact', () => {
    expect(stripStateSuffix('Barcelona-EQU')).toBe('Barcelona-EQU');
    expect(stripStateSuffix('Nacional (URU)')).toBe('Nacional (URU)');
  });

  it('leaves names without suffix unchanged', () => {
    expect(stripStateSuffix('Flamengo')).toBe('Flamengo');
    expect(stripStateSuffix('Santos')).toBe('Santos');
  });
});

describe('normalizeForSearch', () => {
  it('lowercases text', () => {
    expect(normalizeForSearch('Flamengo')).toBe('flamengo');
  });

  it('strips diacritics', () => {
    expect(normalizeForSearch('Grêmio')).toBe('gremio');
    expect(normalizeForSearch('São Paulo')).toBe('sao paulo');
    expect(normalizeForSearch('Atlético')).toBe('atletico');
  });

  it('trims whitespace', () => {
    expect(normalizeForSearch('  Santos  ')).toBe('santos');
  });
});

describe('teamMatches', () => {
  it('matches exact name', () => {
    expect(teamMatches('Flamengo-RJ', 'Flamengo')).toBe(true);
    expect(teamMatches('Flamengo', 'Flamengo')).toBe(true);
  });

  it('matches case-insensitively', () => {
    expect(teamMatches('Palmeiras-SP', 'palmeiras')).toBe(true);
  });

  it('matches accent-insensitively', () => {
    expect(teamMatches('Grêmio-RS', 'Gremio')).toBe(true);
    expect(teamMatches('São Paulo-SP', 'Sao Paulo')).toBe(true);
  });

  it('rejects non-matching team', () => {
    expect(teamMatches('Santos-SP', 'Flamengo')).toBe(false);
    expect(teamMatches('Palmeiras-SP', 'Santos')).toBe(false);
  });

  it('returns false for empty query', () => {
    expect(teamMatches('Santos-SP', '')).toBe(false);
  });
});

describe('parseDate', () => {
  it('converts Brazilian DD/MM/YYYY to ISO', () => {
    expect(parseDate('29/03/2003')).toBe('2003-03-29');
    expect(parseDate('01/12/2019')).toBe('2019-12-01');
  });

  it('strips time from ISO datetime', () => {
    expect(parseDate('2012-05-19 18:30:00')).toBe('2012-05-19');
    expect(parseDate('2023-09-24')).toBe('2023-09-24');
  });

  it('returns empty string for empty input', () => {
    expect(parseDate('')).toBe('');
  });
});

describe('parseGoals', () => {
  it('parses integer strings', () => {
    expect(parseGoals('2')).toBe(2);
    expect(parseGoals('0')).toBe(0);
  });

  it('parses float strings (rounds)', () => {
    expect(parseGoals('1.0')).toBe(1);
    expect(parseGoals('2.0')).toBe(2);
  });

  it('parses numeric values', () => {
    expect(parseGoals(3)).toBe(3);
  });

  it('returns 0 for missing/invalid values', () => {
    expect(parseGoals(undefined)).toBe(0);
    expect(parseGoals('')).toBe(0);
    expect(parseGoals('NA')).toBe(0);
  });
});
