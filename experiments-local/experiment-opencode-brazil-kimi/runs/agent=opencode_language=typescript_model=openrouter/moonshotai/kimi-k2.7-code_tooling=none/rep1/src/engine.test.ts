/*
 * Brazilian Soccer MCP Server - Query engine BDD-style integration tests
 *
 * These tests mirror the Gherkin scenarios from the specification and cover
 * match, team, player, competition, and statistical queries.
 */

import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { loadDataset } from './loader.js';
import { QueryEngine } from './engine.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = resolve(__dirname, '..', 'data', 'kaggle');

let engine: QueryEngine;

beforeAll(async () => {
  const store = await loadDataset(DATA_DIR);
  engine = new QueryEngine(store);
});

describe('Feature: Match Queries', () => {
  describe('Scenario: Find matches between two teams', () => {
    it('returns matches between Flamengo and Fluminense', () => {
      const matches = engine.findMatchesBetween('Flamengo', 'Fluminense');
      expect(matches.length).toBeGreaterThan(0);
      for (const match of matches) {
        const teams = `${match.homeTeam} ${match.awayTeam}`.toLowerCase();
        expect(teams).toContain('flamengo');
        expect(teams).toContain('fluminense');
      }
    });

    it('each match has date, scores, and competition', () => {
      const match = engine.findMatchesBetween('Flamengo', 'Fluminense')[0];
      expect(match.date).toBeTruthy();
      expect(match.homeGoal).not.toBeNull();
      expect(match.awayGoal).not.toBeNull();
      expect(match.competition).toBeTruthy();
    });
  });

  describe('Scenario: Find matches by competition', () => {
    it('returns Copa Libertadores matches', () => {
      const matches = engine.findMatches({ competition: 'Libertadores' });
      expect(matches.length).toBeGreaterThan(0);
      expect(matches.every((m) => m.competition.toLowerCase().includes('libertadores'))).toBe(true);
    });

    it('returns Copa do Brasil finals (highest round)', () => {
      // The Copa do Brasil dataset labels finals as round "8".
      const finals = engine.findMatches({ competition: 'Copa do Brasil', round: '8' });
      expect(finals.length).toBeGreaterThan(0);
    });
  });

  describe('Scenario: Find matches by season', () => {
    it('returns Palmeiras matches in 2023', () => {
      const matches = engine.findMatches({ team: 'Palmeiras', season: 2023 });
      expect(matches.length).toBeGreaterThan(0);
      expect(matches.every((m) => m.season === 2023)).toBe(true);
    });
  });
});

describe('Feature: Team Queries', () => {
  describe('Scenario: Get team statistics', () => {
    it('returns statistics for Palmeiras in season 2023', () => {
      const record = engine.getTeamRecord('Palmeiras', { season: 2023 });
      expect(record.matches).toBeGreaterThan(0);
      expect(record.wins + record.draws + record.losses).toBe(record.matches);
      expect(record.goalsFor).toBeGreaterThanOrEqual(0);
      expect(record.goalsAgainst).toBeGreaterThanOrEqual(0);
    });

    it('returns Corinthians home record in 2022', () => {
      const record = engine.getTeamRecord('Corinthians', { season: 2022 }, 'home');
      expect(record.matches).toBeGreaterThan(0);
      expect(record.team).toBe('Corinthians');
    });
  });

  describe('Scenario: Compare teams head-to-head', () => {
    it('returns wins, losses, and goals for Palmeiras vs Santos', () => {
      const h2h = engine.getHeadToHead('Palmeiras', 'Santos');
      expect(h2h.matches.length).toBeGreaterThan(0);
      expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.matches.length);
    });
  });
});

describe('Feature: Player Queries', () => {
  describe('Scenario: Find Brazilian players', () => {
    it('returns Brazilian players', () => {
      const players = engine.findPlayers({ nationality: 'Brazil' });
      expect(players.length).toBeGreaterThan(0);
      expect(players.every((p) => p.nationality.toLowerCase().includes('brazil'))).toBe(true);
    });

    it('returns highest-rated Santos players', () => {
      const players = engine.findPlayers({ club: 'Santos', limit: 5 });
      expect(players.length).toBeGreaterThan(0);
      expect(players.every((p) => p.club && p.club.toLowerCase().includes('santos'))).toBe(true);
      const sorted = [...players].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
      expect(players).toEqual(sorted);
    });

    it('returns forwards from Fluminense', () => {
      const players = engine.findPlayers({ club: 'Fluminense', position: 'ST', limit: 5 });
      expect(players.length).toBeGreaterThan(0);
      expect(players.every((p) => p.position && p.position.toUpperCase().includes('ST'))).toBe(true);
    });
  });
});

describe('Feature: Competition Queries', () => {
  describe('Scenario: Calculate season standings', () => {
    it('calculates 2019 Brasileirão standings with Flamengo as champion', () => {
      const standings = engine.calculateStandings('Brasileirão', 2019);
      expect(standings.length).toBeGreaterThan(0);
      expect(standings[0].team).toBe('Flamengo');
    });

    it('calculates 2020 Brasileirão relegation zone', () => {
      const standings = engine.calculateStandings('Brasileirão', 2020);
      expect(standings.length).toBeGreaterThan(0);
      const relegated = standings.slice(-4);
      expect(relegated.length).toBe(4);
      expect(relegated.every((s) => s.position !== undefined)).toBe(true);
    });
  });
});

describe('Feature: Statistical Analysis', () => {
  describe('Scenario: Compute dataset averages and biggest wins', () => {
    it('computes average goals per match for Brasileirão', () => {
      const avg = engine.averageGoals({ competition: 'Brasileirão' });
      expect(avg).toBeGreaterThan(0);
      expect(avg).toBeLessThan(10);
    });

    it('returns biggest wins', () => {
      const wins = engine.biggestWins({}, 5);
      expect(wins.length).toBe(5);
      const diff = Math.abs(wins[0].homeGoal! - wins[0].awayGoal!);
      for (const w of wins.slice(1)) {
        expect(Math.abs(w.homeGoal! - w.awayGoal!)).toBeLessThanOrEqual(diff);
      }
    });

    it('computes home win rate', () => {
      const rate = engine.homeWinRate({ competition: 'Brasileirão' });
      expect(rate).toBeGreaterThan(0);
      expect(rate).toBeLessThan(1);
    });
  });
});
