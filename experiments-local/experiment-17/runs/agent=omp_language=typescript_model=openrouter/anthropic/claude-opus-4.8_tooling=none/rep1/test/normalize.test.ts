/**
 * Context
 * =======
 * BDD (Given/When/Then) tests for the normalization layer (src/normalize.ts).
 *
 * These pin the behaviors the spec's "Data Quality Notes" demand: team-name
 * variations (state suffixes, full names, accents) must canonicalize to one key,
 * while genuinely distinct same-base clubs (Atlético-MG vs Athletico-PR) must
 * stay separate; multiple date formats must parse to ISO; competition spellings
 * must map to canonical labels.
 */

import { describe, it, expect } from 'vitest';
import { canonicalTeam, displayTeam, parseDate, canonicalCompetition } from '../src/normalize.js';

describe('Feature: team name normalization', () => {
  it('Given suffix/accent/full-name variants, When canonicalized, Then they collapse to one key', () => {
    // Same club, many spellings across files.
    const key = canonicalTeam('Palmeiras-SP');
    expect(canonicalTeam('Palmeiras')).toBe(key);
    expect(canonicalTeam('Palmeiras - SP')).toBe(key);

    expect(canonicalTeam('Grêmio')).toBe(canonicalTeam('Gremio-RS'));
    expect(canonicalTeam('São Paulo')).toBe(canonicalTeam('Sao Paulo-SP'));
    expect(canonicalTeam('Vasco')).toBe(canonicalTeam('Vasco da Gama-RJ'));
  });

  it('Given full-name spellings, When canonicalized, Then they map onto the short key', () => {
    expect(canonicalTeam('Sport Club do Recife')).toBe(canonicalTeam('Sport-PE'));
    expect(canonicalTeam('Red Bull Bragantino-SP')).toBe(canonicalTeam('Bragantino'));
    expect(canonicalTeam('EC Juventude')).toBe(canonicalTeam('Juventude-RS'));
  });

  it('Given distinct clubs sharing a base name, When canonicalized, Then they stay separate', () => {
    const mineiro = canonicalTeam('Atlético-MG');
    const paranaense = canonicalTeam('Athletico-PR');
    const goianiense = canonicalTeam('Atlético-GO');
    expect(new Set([mineiro, paranaense, goianiense]).size).toBe(3);

    // Full-name spellings still land on the correct distinct key.
    expect(canonicalTeam('Atletico Mineiro')).toBe(mineiro);
    expect(canonicalTeam('Athletico Paranaense')).toBe(paranaense);

    // América MG vs América RN are different clubs.
    expect(canonicalTeam('América-MG')).not.toBe(canonicalTeam('América-RN'));
  });

  it('Given a foreign club with a parenthetical country code, When canonicalized, Then the code disambiguates', () => {
    expect(canonicalTeam('Nacional (URU)')).not.toBe(canonicalTeam('Nacional - AM'));
  });

  it('Given a raw name, When formatted for display, Then accents are kept and redundant suffix dropped', () => {
    expect(displayTeam('Grêmio-RS')).toBe('Grêmio');
    expect(displayTeam('Palmeiras-SP')).toBe('Palmeiras');
    // Ambiguous base keeps the suffix visible.
    expect(displayTeam('Atlético-MG')).toBe('Atlético (MG)');
  });

  it('Given empty input, When canonicalized, Then it returns an empty string', () => {
    expect(canonicalTeam('')).toBe('');
    expect(canonicalTeam(undefined)).toBe('');
  });
});

describe('Feature: date parsing', () => {
  it('Given ISO, Brazilian and datetime formats, When parsed, Then all yield ISO YYYY-MM-DD', () => {
    expect(parseDate('2023-09-24')).toBe('2023-09-24');
    expect(parseDate('2012-05-19 18:30:00')).toBe('2012-05-19');
    expect(parseDate('29/03/2003')).toBe('2003-03-29');
    expect(parseDate('9/3/2003')).toBe('2003-03-09');
  });

  it('Given an unparseable value, When parsed, Then it returns undefined', () => {
    expect(parseDate('not a date')).toBeUndefined();
    expect(parseDate('')).toBeUndefined();
    expect(parseDate(undefined)).toBeUndefined();
  });
});

describe('Feature: competition normalization', () => {
  it('Given competition spellings, When canonicalized, Then they map to canonical labels', () => {
    expect(canonicalCompetition('Brasileirão')).toBe('Brasileirão Série A');
    expect(canonicalCompetition('Serie A')).toBe('Brasileirão Série A');
    expect(canonicalCompetition('brasileiro')).toBe('Brasileirão Série A');
    expect(canonicalCompetition('Serie B')).toBe('Brasileirão Série B');
    expect(canonicalCompetition('Copa do Brasil')).toBe('Copa do Brasil');
    expect(canonicalCompetition('Libertadores')).toBe('Copa Libertadores');
  });

  it('Given an unknown competition, When canonicalized, Then it returns undefined', () => {
    expect(canonicalCompetition('Premier League')).toBeUndefined();
    expect(canonicalCompetition('')).toBeUndefined();
  });
});
