/**
 * Unit tests for normalization utilities.
 */

import { describe, it, expect } from 'vitest';
import { normalizeTeamName, teamMatchesSearch, parseDate, parseGoals } from '../src/data/normalize.js';

describe('normalizeTeamName', () => {
  it('strips "-XX" state suffix (Brasileirao format)', () => {
    expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    expect(normalizeTeamName('Atletico-MG')).toBe('Atletico');
  });

  it('strips " - XX" state suffix (Copa do Brasil format)', () => {
    expect(normalizeTeamName('América - MG')).toBe('América');
    expect(normalizeTeamName('Bahia - BA')).toBe('Bahia');
  });

  it('leaves names without suffix unchanged', () => {
    expect(normalizeTeamName('Flamengo')).toBe('Flamengo');
    expect(normalizeTeamName('Sao Paulo')).toBe('Sao Paulo');
  });

  it('trims whitespace', () => {
    expect(normalizeTeamName('  Palmeiras-SP  ')).toBe('Palmeiras');
  });
});

describe('teamMatchesSearch', () => {
  it('matches team with state suffix against search without suffix', () => {
    expect(teamMatchesSearch('Palmeiras-SP', 'Palmeiras')).toBe(true);
    expect(teamMatchesSearch('Flamengo-RJ', 'Flamengo')).toBe(true);
  });

  it('matches search with state suffix against team without suffix', () => {
    expect(teamMatchesSearch('Palmeiras', 'Palmeiras-SP')).toBe(true);
  });

  it('is case-insensitive', () => {
    expect(teamMatchesSearch('Palmeiras-SP', 'palmeiras')).toBe(true);
    expect(teamMatchesSearch('FLAMENGO', 'flamengo')).toBe(true);
  });

  it('supports partial matching', () => {
    expect(teamMatchesSearch('Sport Club Corinthians Paulista', 'Corinthians')).toBe(true);
  });

  it('does not match unrelated teams', () => {
    expect(teamMatchesSearch('Palmeiras-SP', 'Flamengo')).toBe(false);
  });

  it('returns true for empty search term', () => {
    expect(teamMatchesSearch('Palmeiras', '')).toBe(true);
  });
});

describe('parseDate', () => {
  it('parses ISO format with time', () => {
    expect(parseDate('2012-05-19 18:30:00')).toBe('2012-05-19');
  });

  it('parses ISO format without time', () => {
    expect(parseDate('2023-09-24')).toBe('2023-09-24');
  });

  it('parses Brazilian DD/MM/YYYY format', () => {
    expect(parseDate('29/03/2003')).toBe('2003-03-29');
    expect(parseDate('01/07/2019')).toBe('2019-07-01');
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

  it('parses float strings and rounds', () => {
    expect(parseGoals('1.0')).toBe(1);
    expect(parseGoals('2.0')).toBe(2);
  });

  it('returns 0 for empty/undefined', () => {
    expect(parseGoals('')).toBe(0);
    expect(parseGoals(undefined)).toBe(0);
  });
});
