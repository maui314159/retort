import { describe, it, expect, beforeAll } from 'vitest';
import { DataManager, cleanForSearch } from '../src/data-loader.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.join(__dirname, '..', 'data', 'kaggle');

describe('cleanForSearch', () => {
  it('removes state suffixes', () => {
    expect(cleanForSearch('Palmeiras-SP')).toBe('palmeiras');
    expect(cleanForSearch('Flamengo-RJ')).toBe('flamengo');
  });

  it('removes accents', () => {
    expect(cleanForSearch('São Paulo')).toBe('sao paulo');
    expect(cleanForSearch('Grêmio')).toBe('gremio');
  });
});

describe('DataManager', () => {
  let manager: DataManager;

  beforeAll(async () => {
    manager = new DataManager(dataDir);
    await manager.load();
  });

  it('loads matches', () => {
    const matches = manager.searchMatches({ team: 'Flamengo' });
    expect(matches.length).toBeGreaterThan(0);
  });

  it('loads extended match data', () => {
    const matches = manager.searchMatches({ competition: 'Copa do Brasil', season: '2023' });
    expect(matches.length).toBeGreaterThan(0);
  });
  it('loads players', () => {
    const players = manager.searchPlayers({ nationality: 'Brazil' });
    expect(players.length).toBeGreaterThan(0);
  });

  it('calculates team stats', () => {
    const stats = manager.getTeamStats('Flamengo', '2019');
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
  });

  it('calculates head to head', () => {
    const h2h = manager.getHeadToHead('Flamengo', 'Fluminense');
    expect(h2h.matches).toBeGreaterThan(0);
    expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.matches);
  });

  it('calculates standings', () => {
    const standings = manager.getCompetitionStandings('Brasileirao', '2019');
    expect(standings.length).toBeGreaterThan(0);
    expect(standings[0].team).toBeDefined();
  });

  it('searches players by club', () => {
    const players = manager.searchPlayers({ club: 'Grêmio', minOverall: 65 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.overall).toBeGreaterThanOrEqual(65);
    }
  });
});
