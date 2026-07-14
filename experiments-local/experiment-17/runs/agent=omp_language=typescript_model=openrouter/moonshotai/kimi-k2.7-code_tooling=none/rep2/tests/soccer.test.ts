/**
 * Brazilian Soccer MCP Server
 * Behavior-Driven Development tests covering match, team, player,
 * competition, and statistical queries.
 */

import { loadRepository, matchesTeam, SoccerRepository } from '../src/data.js';
import { TOOLS, createToolRunner, createServer } from '../src/server.js';
import {
  bestAwayRecord,
  competitionStandings,
  competitionStats,
  findMatches,
  findPlayers,
  formatHeadToHead,
  formatMatchList,
  formatTeamStats,
  headToHead,
  teamStatistics,
} from '../src/queries.js';

let repo: SoccerRepository;

beforeAll(async () => {
  repo = await loadRepository();
});

describe('Data loading', () => {
  it('loads all six CSV files', () => {
    expect(repo.matches.length).toBeGreaterThan(0);
    expect(repo.players.length).toBeGreaterThan(0);
    expect(repo.competitions.length).toBeGreaterThanOrEqual(3);
  });

  it('covers the expected competitions', () => {
    const names = new Set(repo.competitions);
    expect(names.has('Brasileirão')).toBe(true);
    expect(names.has('Copa do Brasil')).toBe(true);
    expect(names.has('Copa Libertadores')).toBe(true);
  });
});

describe('Match Queries', () => {
  it('finds matches between Flamengo and Fluminense', () => {
    const matches = findMatches(repo, { teamA: 'Flamengo', teamB: 'Fluminense' });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(
        (matchesTeam(m.homeTeam, 'Flamengo') || matchesTeam(m.awayTeam, 'Flamengo')) &&
          (matchesTeam(m.homeTeam, 'Fluminense') || matchesTeam(m.awayTeam, 'Fluminense'))
      ).toBe(true);
      expect(m.datetime).not.toBeNull();
    }
  });

  it('finds Palmeiras matches in 2023', () => {
    const matches = findMatches(repo, { team: 'Palmeiras', season: 2023 });
    expect(matches.length).toBeGreaterThan(0);
    expect(matches.every((m) => m.season === 2023)).toBe(true);
  });

  it('finds Copa do Brasil late-stage matches', () => {
    const matches = findMatches(repo, { competition: 'Copa do Brasil', round: '8' });
    expect(matches.length).toBeGreaterThan(0);
    expect(matches.every((m) => m.competition === 'Copa do Brasil')).toBe(true);
  });
});

describe('Team Queries', () => {
  it('returns Corinthians home record in 2022 Brasileirão', () => {
    const stats = teamStatistics(repo, 'Corinthians', {
      season: 2022,
      competition: 'Brasileirão',
      venue: 'home',
    });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.matches).toEqual(stats.wins + stats.draws + stats.losses);
    expect(stats.winRate).toBeGreaterThanOrEqual(0);
    expect(stats.winRate).toBeLessThanOrEqual(100);
  });

  it('calculates head-to-head between Palmeiras and Santos', () => {
    const result = headToHead(repo, 'Palmeiras', 'Santos');
    expect(result.matches.length).toBeGreaterThan(0);
    expect(result.winsA + result.winsB + result.draws).toEqual(
      result.matches.filter((m) => m.homeGoals !== null && m.awayGoals !== null).length
    );
    expect(formatHeadToHead(result)).toContain(result.teamA);
    expect(formatHeadToHead(result)).toContain(result.teamB);
  });
});

describe('Player Queries', () => {
  it('finds Brazilian players', () => {
    const players = findPlayers(repo, { nationality: 'Brazil' });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].nationality?.toLowerCase()).toContain('brazil');
  });

  it('finds players at Grêmio sorted by overall rating', () => {
    const players = findPlayers(repo, { club: 'Grêmio' });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].club?.toLowerCase()).toContain('grêmio');
    for (let i = 1; i < players.length; i++) {
      expect(players[i - 1].overall ?? 0).toBeGreaterThanOrEqual(players[i].overall ?? 0);
    }
  });

  it('finds forwards from Grêmio', () => {
    const players = findPlayers(repo, { club: 'Grêmio', position: 'ST' });
    expect(players.length).toBeGreaterThan(0);
  });
});

describe('Competition Queries', () => {
  it('calculates 2019 Brasileirão standings with Flamengo as champion', () => {
    const standings = competitionStandings(repo, 'Brasileirão', 2019);
    expect(standings.length).toBeGreaterThan(0);
    expect(standings[0].team.toLowerCase()).toContain('flamengo');
    expect(standings[0].position).toBe(1);
  });

  it('calculates competition-level statistics', () => {
    const stats = competitionStats(repo, 'Brasileirão');
    expect(stats.totalMatches).toBeGreaterThan(0);
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(0);
    expect(stats.homeWinRate + stats.drawRate + stats.awayWinRate).toBeCloseTo(100, 1);
    expect(stats.biggestWins.length).toBeGreaterThan(0);
  });

  it('finds teams with best away records', () => {
    const records = bestAwayRecord(repo, 'Brasileirão');
    expect(records.length).toBeGreaterThan(0);
    expect(records[0].matches).toBeGreaterThanOrEqual(5);
    expect(records.every((r) => r.winRate >= 0 && r.winRate <= 100)).toBe(true);
  });
});

describe('MCP server tools', () => {
  it('exports the expected tools', () => {
    expect(TOOLS.length).toBeGreaterThanOrEqual(7);
    const names = TOOLS.map((t) => t.name);
    expect(names).toContain('search_matches');
    expect(names).toContain('search_players');
    expect(names).toContain('competition_standings');
  });

  it('returns match search results via the tool runner', async () => {
    const runTool = createToolRunner(repo);
    const result = await runTool('search_matches', {
      team: 'Palmeiras',
      season: 2023,
      limit: 5,
    });
    expect(result.content[0]).toEqual(
      expect.objectContaining({
        type: 'text',
        text: expect.stringContaining('Palmeiras'),
      })
    );
  });

  it('returns player search results via the tool runner', async () => {
    const runTool = createToolRunner(repo);
    const result = await runTool('search_players', {
      nationality: 'Brazil',
      limit: 3,
    });
    expect(result.content[0]).toEqual(
      expect.objectContaining({
        type: 'text',
        text: expect.stringContaining('Brazil'),
      })
    );
  });

  it('creates a server instance', async () => {
    const server = await createServer(repo);
    expect(server).toBeDefined();
  });
});

describe('Formatting', () => {
  it('formats a match list', () => {
    const text = formatMatchList(repo.matches.slice(0, 3));
    expect(text).toContain('-');
    expect(text).toMatch(/\d+/);
  });

  it('formats team statistics', () => {
    const stats = teamStatistics(repo, 'Flamengo');
    const text = formatTeamStats(stats);
    expect(text).toContain('Flamengo');
    expect(text).toContain('Win rate');
  });
});
