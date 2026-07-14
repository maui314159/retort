/**
 * brazilian-soccer-mcp / tests/queries.test.ts
 *
 * BDD (Given/When/Then) tests for the query layer.
 *
 * Context block:
 * Exercises the normalized data and query functions against the real Kaggle
 * datasets, structured as Gherkin-style scenarios mirroring the TASK.md
 * "Testing Approach" section. Covers the success criteria: all 6 CSV files
 * load, matches search by team/competition/season, team statistics, head to
 * head, standings, aggregate stats, biggest wins, and player search with name
 * normalization across the different team-name conventions.
 */

import { describe, it, expect } from 'vitest';
import { loadMatches, loadPlayers, resetCache } from '../src/data-loader.js';
import {
  findMatches, headToHead, headToHeadMatches, teamStats, aggregateStats,
  biggestWins, standings, findPlayers, brazilianClubsSummary,
} from '../src/queries.js';
import { teamKey, cleanTeamName } from '../src/team-normalizer.js';

describe('Feature: Data loading', () => {
  /*
   * Scenario: All six CSV files are loadable and queryable
   *   Given the datasets in data/kaggle/
   *   When the loader reads them
   *   Then matches and players arrays are non-empty
   *   And every match has a competition label
   */
  it('loads matches and players from all CSV files', () => {
    resetCache();
    const matches = loadMatches();
    const players = loadPlayers();
    expect(matches.length).toBeGreaterThan(20000);
    expect(players.length).toBeGreaterThan(18000);
    for (const m of matches.slice(0, 1000)) {
      expect(m.competition.length).toBeGreaterThan(0);
      expect(m.homeTeamKey.length).toBeGreaterThan(0);
      expect(m.awayTeamKey.length).toBeGreaterThan(0);
    }
  });
});

describe('Feature: Team name normalization', () => {
  /*
   * Scenario: Team name variations resolve to one canonical key
   *   Given names with state suffixes, country markers, and accents
   *   When normalized
   *   Then "Palmeiras-SP", "Palmeiras" share a key
   *   And "São Paulo" matches "Sao Paulo"
   */
  it('folds state suffixes, country markers, and accents', () => {
    expect(teamKey('Palmeiras-SP')).toBe(teamKey('Palmeiras'));
    expect(teamKey('Flamengo-RJ')).toBe(teamKey('Flamengo'));
    expect(teamKey('São Paulo')).toBe(teamKey('Sao Paulo'));
    expect(teamKey('Nacional (URU)')).toBe(teamKey('Nacional'));
    expect(teamKey('Boavista Sport Club (antigo Esporte Clube Barreira) - RJ'))
      .toBe(teamKey('Boavista Sport Club'));
  });

  it('keeps a human-readable cleaned display name', () => {
    expect(cleanTeamName('Palmeiras-SP')).toBe('Palmeiras');
    expect(cleanTeamName('Nacional (URU)')).toBe('Nacional');
  });
});

describe('Feature: Match Queries', () => {
  /*
   * Scenario: Find matches between two teams
   *   Given the match data is loaded
   *   When I search for matches between "Flamengo" and "Fluminense"
   *   Then I should receive a list of matches
   *   And each match should have date, scores, and competition
   */
  it('finds Flamengo vs Fluminense matches across datasets', () => {
    const matches = loadMatches();
    const games = headToHeadMatches(matches, 'Flamengo', 'Fluminense');
    expect(games.length).toBeGreaterThan(10);
    for (const m of games) {
      const teams = [m.homeTeamKey, m.awayTeamKey].sort();
      expect(teams).toEqual(['flamengo', 'fluminense'].sort());
      expect(m.competition.length).toBeGreaterThan(0);
    }
  });

  /*
   * Scenario: Filter by competition and season
   *   Given matches loaded
   *   When searching Brasileirão 2023 for Palmeiras
   *   Then every result is in 2023 and involves Palmeiras
   */
  it('filters by competition, season, and team together', () => {
    const matches = loadMatches();
    const found = findMatches(matches, {
      team: 'Palmeiras', competition: 'Brasileirão', season: 2023,
    });
    expect(found.length).toBeGreaterThan(0);
    for (const m of found) {
      expect(m.season).toBe(2023);
      expect([m.homeTeamKey, m.awayTeamKey]).toContain(teamKey('Palmeiras'));
      expect(m.competition.toLowerCase()).toContain('brasileir');
    }
  });

  it('finds matches by Copa do Brasil competition', () => {
    const matches = loadMatches();
    const found = findMatches(matches, { competition: 'Copa do Brasil' });
    expect(found.length).toBeGreaterThan(100);
    for (const m of found.slice(0, 50)) {
      expect(m.competition).toBe('Copa do Brasil');
    }
  });
});

describe('Feature: Team Queries', () => {
  /*
   * Scenario: Get team statistics
   *   Given the match data is loaded
   *   When I request statistics for "Palmeiras" in season "2023"
   *   Then I should receive wins, losses, draws, and goals
   */
  it('computes Palmeiras 2023 statistics', () => {
    const matches = loadMatches();
    const stats = teamStats(matches, 'Palmeiras', { season: 2023, competition: 'Brasileirão' });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThanOrEqual(0);
    expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
    expect(stats.points).toBe(stats.wins * 3 + stats.draws);
  });

  it('separates home and away records via the venue filter', () => {
    const matches = loadMatches();
    const home = teamStats(matches, 'Flamengo', { season: 2023, venue: 'home' });
    const away = teamStats(matches, 'Flamengo', { season: 2023, venue: 'away' });
    expect(home.matches).toBeGreaterThan(0);
    expect(away.matches).toBeGreaterThan(0);
  });
});

describe('Feature: Head-to-Head', () => {
  /*
   * Scenario: Compare two teams head-to-head
   *   Given matches loaded
   *   When comparing Palmeiras and Santos
   *   Then wins + draws + losses equals total matches with scores
   */
  it('summarizes Palmeiras vs Santos', () => {
    const matches = loadMatches();
    const h2h = headToHead(matches, 'Palmeiras', 'Santos');
    expect(h2h.matches).toBeGreaterThan(0);
    expect(h2h.aWins + h2h.bWins + h2h.draws).toBeLessThanOrEqual(h2h.matches);
    expect(h2h.teamA).toBe('Palmeiras');
    expect(h2h.teamB).toBe('Santos');
  });
});

describe('Feature: Competition Queries', () => {
  /*
   * Scenario: Compute standings for a season
   *   Given matches loaded
   *   When I request 2019 Brasileirão standings
   *   Then the table is sorted by points desc and position 1 is the champion
   */
  it('computes 2019 Brasileirão standings sorted by points', () => {
    const matches = loadMatches();
    const rows = standings(matches, 'Brasileirão', 2019);
    expect(rows.length).toBeGreaterThan(10);
    for (let i = 1; i < rows.length; i++) {
      const prev = rows[i - 1];
      const cur = rows[i];
      const prevTiebreak = prev.points * 100000 + prev.wins * 1000 + prev.goalDifference;
      const curTiebreak = cur.points * 100000 + cur.wins * 1000 + cur.goalDifference;
      expect(prevTiebreak).toBeGreaterThanOrEqual(curTiebreak);
    }
    expect(rows[0].position).toBe(1);
  });
});

describe('Feature: Statistical Analysis', () => {
  /*
   * Scenario: Aggregate stats over a competition
   *   Given matches loaded
   *   When I aggregate Brasileirão matches
   *   Then home + away + draw rates sum to ~1.0
   *   And average goals per match is positive
   */
  it('aggregates Brasileirão stats with rates summing to 1', () => {
    const matches = loadMatches();
    const scoped = findMatches(matches, { competition: 'Brasileirão' });
    const stats = aggregateStats(scoped);
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(0);
    const totalRate = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
    expect(totalRate).toBeCloseTo(1.0, 5);
  });

  /*
   * Scenario: Biggest wins are ordered by goal difference
   *   Given matches loaded
   *   When I request the biggest victories
   *   Then the first result has the largest goal difference
   */
  it('returns biggest wins ordered by goal difference', () => {
    const matches = loadMatches();
    const top = biggestWins(matches, 5);
    expect(top.length).toBe(5);
    const diffs = top.map((m) => Math.abs((m.homeGoals ?? 0) - (m.awayGoals ?? 0)));
    for (let i = 1; i < diffs.length; i++) {
      expect(diffs[i - 1]).toBeGreaterThanOrEqual(diffs[i]);
    }
    expect(diffs[0]).toBeGreaterThanOrEqual(4);
  });
});

describe('Feature: Player Queries', () => {
  /*
   * Scenario: Find Brazilian players
   *   Given the FIFA dataset loaded
   *   When I filter nationality "Brazil"
   *   Then every result is Brazilian and ranked by overall desc
   */
  it('finds Brazilian players ranked by overall', () => {
    const players = loadPlayers();
    const found = findPlayers(players, { nationality: 'Brazil', limit: 10 });
    expect(found.length).toBe(10);
    for (const p of found) {
      expect(p.nationalityKey).toBe('brazil');
    }
    for (let i = 1; i < found.length; i++) {
      expect((found[i - 1].overall ?? 0)).toBeGreaterThanOrEqual((found[i].overall ?? 0));
    }
  });

  it('finds players by name substring (accent-insensitive)', () => {
    const players = loadPlayers();
    const found = findPlayers(players, { name: 'Neymar' });
    expect(found.length).toBeGreaterThan(0);
    expect(found.some((p) => p.name.toLowerCase().includes('neymar'))).toBe(true);
  });

  it('summarizes Brazilian players at Brazilian clubs', () => {
    const players = loadPlayers();
    const summary = brazilianClubsSummary(players);
    expect(summary.length).toBeGreaterThan(0);
    for (const s of summary) {
      expect(s.count).toBeGreaterThan(0);
      expect(s.club.length).toBeGreaterThan(0);
    }
  });
});
