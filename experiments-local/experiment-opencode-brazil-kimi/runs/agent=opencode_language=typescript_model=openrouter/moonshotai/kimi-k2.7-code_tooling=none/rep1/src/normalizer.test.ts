/*
 * Brazilian Soccer MCP Server - Normalizer unit tests
 */

import {
  normalizeTeamName,
  teamNamesMatch,
  teamNameContains,
  parseBrazilianDate,
  parseNumber,
  parseIntSafe,
  formatDateISO,
  parseYear
} from './normalizer.js';

describe('Normalizer', () => {
  describe('normalizeTeamName', () => {
    it('removes state suffixes like -SP and -RJ', () => {
      expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
      expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    });

    it('handles UTF-8 accented names', () => {
      expect(normalizeTeamName('Grêmio')).toBe('Gremio');
      expect(normalizeTeamName('São Paulo')).toBe('Sao Paulo');
    });

    it('maps known historical name variants to canonical forms', () => {
      expect(normalizeTeamName('Atlético-MG')).toBe('Atletico Mineiro');
      expect(normalizeTeamName('Athletico-PR')).toBe('Athletico Paranaense');
    });
  });

  describe('teamNamesMatch', () => {
    it('matches names with and without state suffixes', () => {
      expect(teamNamesMatch('Palmeiras-SP', 'Palmeiras')).toBe(true);
      expect(teamNamesMatch('Flamengo', 'Flamengo-RJ')).toBe(true);
    });

    it('matches accented and canonical forms', () => {
      expect(teamNamesMatch('São Paulo', 'Sao Paulo')).toBe(true);
    });

    it('does not match unrelated teams', () => {
      expect(teamNamesMatch('Palmeiras', 'Flamengo')).toBe(false);
    });
  });

  describe('teamNameContains', () => {
    it('matches substring after normalization', () => {
      expect(teamNameContains('Sport Club Corinthians Paulista', 'Corinthians')).toBe(true);
    });
  });

  describe('parseBrazilianDate', () => {
    it('parses ISO date-time strings', () => {
      const date = parseBrazilianDate('2012-05-19 18:30:00');
      expect(date).not.toBeNull();
      expect(formatDateISO(date)).toBe('2012-05-19');
    });

    it('parses Brazilian DD/MM/YYYY format', () => {
      const date = parseBrazilianDate('29/03/2003');
      expect(date).not.toBeNull();
      expect(formatDateISO(date)).toBe('2003-03-29');
    });

    it('parses plain ISO dates', () => {
      const date = parseBrazilianDate('2023-09-24');
      expect(formatDateISO(date)).toBe('2023-09-24');
    });

    it('returns null for invalid input', () => {
      expect(parseBrazilianDate('')).toBeNull();
      expect(parseBrazilianDate('not-a-date')).toBeNull();
    });
  });

  describe('parseNumber', () => {
    it('parses decimal strings with trailing .0', () => {
      expect(parseNumber('1.0')).toBe(1);
    });

    it('parses integers', () => {
      expect(parseNumber('7')).toBe(7);
      expect(parseIntSafe('7')).toBe(7);
    });

    it('returns null for empty input', () => {
      expect(parseNumber('')).toBeNull();
    });
  });

  describe('parseYear', () => {
    it('accepts realistic years', () => {
      expect(parseYear('2023')).toBe(2023);
    });

    it('rejects out-of-range values', () => {
      expect(parseYear('99999')).toBeNull();
    });
  });
});
