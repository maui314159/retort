import { describe, it, expect, beforeAll } from 'vitest';
import { loadData } from '../src/loader.js';
import { createQueryEngine } from '../src/engine.js';

describe('Data loader', () => {
  it('loads all 6 CSV files', async () => {
    const data = await loadData();
    expect(data.matches.length).toBeGreaterThan(20000);
    expect(data.players.length).toBeGreaterThan(18000);
  });
});

describe('Match Queries', () => {
  let engine: ReturnType<typeof createQueryEngine>;

  beforeAll(async () => {
    const data = await loadData();
    engine = createQueryEngine(data);
  });

  it('finds matches between two teams', () => {
    const matches = engine.findMatches({ team1: 'Flamengo', team2: 'Fluminense' });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      const teams = [m.home_team.toLowerCase(), m.away_team.toLowerCase()];
      expect(teams).toContain('flamengo');
      expect(teams).toContain('fluminense');
      expect(m.date).toBeDefined();
      expect(typeof m.home_goal).toBe('number');
      expect(typeof m.away_goal).toBe('number');
    }
  });

  it('filters Palmeiras matches in season 2023', () => {
    const matches = engine.findMatches({ team: 'Palmeiras', season: 2023 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2023);
      const teams = [m.home_team.toLowerCase(), m.away_team.toLowerCase()];
      expect(teams).toContain('palmeiras');
    }
  });

  it('handles team name variations', () => {
    const matches = engine.findMatches({ team: 'Palmeiras-SP' });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      const teams = [m.home_team.toLowerCase(), m.away_team.toLowerCase()];
      expect(teams).toContain('palmeiras');
    }
  });
});

describe('Team Queries', () => {
  let engine: ReturnType<typeof createQueryEngine>;

  beforeAll(async () => {
    const data = await loadData();
    engine = createQueryEngine(data);
  });

  it('returns team statistics with wins, losses, draws, and goals', () => {
    const stats = engine.getTeamStats('Palmeiras', { season: 2022, competition: 'Brasileirão' });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThanOrEqual(0);
    expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it('compares teams head-to-head', () => {
    const h2h = engine.getHeadToHead('Corinthians', 'São Paulo');
    expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.matches.length);
  });
});

describe('Player Queries', () => {
  let engine: ReturnType<typeof createQueryEngine>;

  beforeAll(async () => {
    const data = await loadData();
    engine = createQueryEngine(data);
  });

  it('finds Brazilian players', () => {
    const players = engine.searchPlayers({ nationality: 'Brazil', limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.nationality?.toLowerCase()).toBe('brazil');
    }
  });

  it('finds players by club', () => {
    const players = engine.searchPlayers({ club: 'Flamengo', nationality: 'Brazil', limit: 5 });
    for (const p of players) {
      expect(p.nationality?.toLowerCase()).toBe('brazil');
    }
  });
});

describe('Competition Queries', () => {
  let engine: ReturnType<typeof createQueryEngine>;

  beforeAll(async () => {
    const data = await loadData();
    engine = createQueryEngine(data);
  });

  it('calculates Brasileirão 2019 standings', () => {
    const standings = engine.getStandings('Brasileirão', 2019);
    expect(standings.length).toBeGreaterThan(10);
    const champion = standings[0];
    expect(champion.points).toBeGreaterThan(0);
    expect(champion.wins + champion.draws + champion.losses).toBeGreaterThan(0);
  });
});

describe('Statistical Analysis', () => {
  let engine: ReturnType<typeof createQueryEngine>;

  beforeAll(async () => {
    const data = await loadData();
    engine = createQueryEngine(data);
  });

  it('computes average goals and home win rate', () => {
    const summary = engine.getStatsSummary({ competition: 'Brasileirão' });
    expect(summary.totalMatches).toBeGreaterThan(0);
    expect(summary.averageGoalsPerMatch).toBeGreaterThan(0);
    expect(summary.homeWinRate).toBeGreaterThan(0);
  });
});
