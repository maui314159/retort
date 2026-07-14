/**
 * Brazilian Soccer MCP Server - BDD Test Suite
 *
 * Behavior-driven tests verifying all query capabilities.
 * Uses Node.js native test runner with describe/it.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { loadAllData, getMatches, getPlayers, getMatchCount, getPlayerCount } from '../src/data.js';
import { normalizeTeam } from '../src/normalize.js';
import {
  searchMatches,
  getTeamRecord,
  getHeadToHead,
  searchPlayers,
  getStandings,
  getBiggestWins,
  getAverageGoals,
  getHomeAwayStats,
  getTopScoringTeams,
  getTeamBestAwayRecord,
  getCompetitionList,
  getSeasonList,
} from '../src/queries.js';

// ── Setup ────────────────────────────────────────────────────────────

loadAllData();

// ── Data Loading ─────────────────────────────────────────────────────

describe('Data Loading', () => {
  it('loads all 6 CSV files', () => {
    assert.ok(getMatchCount() > 0, 'matches should be loaded');
    assert.ok(getPlayerCount() > 0, 'players should be loaded');
  });

  it('contains Brasileirao matches', () => {
    const bras = getMatches().filter(m => m.competition === 'brasileirao');
    assert.ok(bras.length > 1000, `should have >1000 Brasileirao matches, got ${bras.length}`);
  });

  it('contains Copa do Brasil matches', () => {
    const cdb = getMatches().filter(m => m.competition === 'copa_do_brasil');
    assert.ok(cdb.length > 500, `should have >500 Copa do Brasil matches, got ${cdb.length}`);
  });

  it('contains Libertadores matches', () => {
    const lib = getMatches().filter(m => m.competition === 'libertadores');
    assert.ok(lib.length > 500, `should have >500 Libertadores matches, got ${lib.length}`);
  });

  it('contains FIFA players', () => {
    const players = getPlayers();
    assert.ok(players.length > 15000, `should have >15000 players, got ${players.length}`);
  });
});

// ── Team Name Normalization ──────────────────────────────────────────

describe('Team Name Normalization', () => {
  it('strips state suffix', () => {
    const result = normalizeTeam('Palmeiras-SP');
    assert.equal(result.key, 'palmeiras');
    assert.equal(result.display, 'Palmeiras');
  });

  it('handles names without suffix', () => {
    const result = normalizeTeam('Flamengo');
    assert.equal(result.key, 'flamengo');
  });

  it('normalizes accented characters', () => {
    const result = normalizeTeam('São Paulo');
    assert.equal(result.key, 'sao paulo');
  });

  it('handles parenthetical asides', () => {
    const result = normalizeTeam('Boavista Sport Club (antigo Esporte Clube Barreira) - RJ');
    assert.equal(result.key, 'boavista sport club');
  });

  it('normalizes Grêmio', () => {
    const result = normalizeTeam('Grêmio-RS');
    assert.equal(result.key, 'gremio');
  });
});

// ── Match Queries ────────────────────────────────────────────────────

describe('Match Queries', () => {
  it('finds matches by team name', () => {
    const results = searchMatches({ team: 'Flamengo', limit: 10 });
    assert.ok(results.length > 0, 'should find Flamengo matches');
    for (const m of results) {
      assert.ok(
        m.homeTeam === 'flamengo' || m.awayTeam === 'flamengo',
        `match should involve Flamengo, got ${m.homeTeamDisplay} vs ${m.awayTeamDisplay}`
      );
    }
  });

  it('finds matches between two teams', () => {
    const results = searchMatches({ team: 'Flamengo', opponent: 'Fluminense' });
    assert.ok(results.length > 0, 'should find Flamengo vs Fluminense matches');
    for (const m of results) {
      const teams = [m.homeTeam, m.awayTeam].sort();
      assert.deepEqual(teams, ['flamengo', 'fluminense']);
    }
  });

  it('filters by competition', () => {
    const results = searchMatches({ competition: 'brasileirao', limit: 5 });
    for (const m of results) {
      assert.equal(m.competition, 'brasileirao');
    }
  });

  it('filters by season', () => {
    const results = searchMatches({ season: 2023, limit: 10 });
    assert.ok(results.length > 0, 'should find 2023 matches');
    for (const m of results) {
      assert.equal(m.season, 2023);
    }
  });

  it('filters by date range', () => {
    const results = searchMatches({ dateFrom: '2023-01-01', dateTo: '2023-12-31', limit: 10 });
    for (const m of results) {
      assert.ok(m.date >= '2023-01-01', `date ${m.date} should be >= 2023-01-01`);
      assert.ok(m.date <= '2023-12-31', `date ${m.date} should be <= 2023-12-31`);
    }
  });

  it('respects result limit', () => {
    const results = searchMatches({ team: 'Flamengo', limit: 5 });
    assert.ok(results.length <= 5, `should return at most 5, got ${results.length}`);
  });

  it('returns empty for non-existent team', () => {
    const results = searchMatches({ team: 'NonExistentTeamXYZ' });
    assert.equal(results.length, 0);
  });
});

// ── Team Statistics ──────────────────────────────────────────────────

describe('Team Statistics', () => {
  it('returns team record', () => {
    const record = getTeamRecord('Flamengo');
    assert.ok(record, 'should find Flamengo record');
    assert.ok(record!.matches > 0, 'should have matches');
    assert.equal(record!.wins + record!.draws + record!.losses, record!.matches);
    assert.equal(record!.points, record!.wins * 3 + record!.draws);
  });

  it('has home and away splits', () => {
    const record = getTeamRecord('Palmeiras');
    assert.ok(record, 'should find Palmeiras record');
    assert.equal(record!.homeStats.matches + record!.awayStats.matches, record!.matches);
  });

  it('has per-competition breakdown', () => {
    const record = getTeamRecord('Corinthians');
    assert.ok(record, 'should find Corinthians record');
    assert.ok(Object.keys(record!.competitions).length > 0, 'should have competition breakdown');
  });

  it('returns null for unknown team', () => {
    assert.equal(getTeamRecord('UnknownTeamXYZ'), null);
  });
});

// ── Head-to-Head ─────────────────────────────────────────────────────

describe('Head-to-Head', () => {
  it('returns head-to-head between two big clubs', () => {
    const h2h = getHeadToHead('Flamengo', 'Palmeiras');
    assert.ok(h2h, 'should find Flamengo vs Palmeiras matches');
    assert.ok(h2h!.totalMatches > 0, 'should have matches');
    assert.equal(
      h2h!.team1Wins + h2h!.team2Wins + h2h!.draws,
      h2h!.totalMatches,
      'wins + draws should equal total'
    );
  });

  it('returns null for teams that never played', () => {
    assert.equal(getHeadToHead('Flamengo', 'Barcelona'), null);
  });
});

// ── Player Queries ───────────────────────────────────────────────────

describe('Player Queries', () => {
  it('finds players by name', () => {
    const results = searchPlayers({ name: 'Neymar' });
    assert.ok(results.length > 0, 'should find Neymar');
    assert.ok(results.some(p => p.name.toLowerCase().includes('neymar')));
  });

  it('filters by nationality', () => {
    const results = searchPlayers({ nationality: 'Brazil', limit: 20 });
    assert.ok(results.length > 0, 'should find Brazilian players');
    for (const p of results) {
      assert.equal(p.nationality.toLowerCase(), 'brazil');
    }
  });

  it('filters by club', () => {
    const results = searchPlayers({ club: 'Fluminense', limit: 20 });
    assert.ok(results.length > 0, 'should find Fluminense players');
    for (const p of results) {
      assert.ok(p.club.includes('fluminense') || p.clubDisplay.toLowerCase().includes('fluminense'));
    }
  });

  it('filters by minimum rating', () => {
    const results = searchPlayers({ minRating: 85, limit: 10 });
    for (const p of results) {
      assert.ok(p.overall >= 85, `rating ${p.overall} should be >= 85`);
    }
  });

  it('sorts by overall rating descending by default', () => {
    const results = searchPlayers({ limit: 10 });
    for (let i = 1; i < results.length; i++) {
      assert.ok(results[i - 1].overall >= results[i].overall, 'should be sorted by overall desc');
    }
  });
});

// ── Competition Standings ────────────────────────────────────────────

describe('Competition Standings', () => {
  it('returns standings for Brasileirao', () => {
    const standings = getStandings('brasileirao', 2023);
    assert.ok(standings.length > 0, 'should have 2023 Brasileirao standings');
    // Verify sorting: first should have most points
    for (let i = 1; i < standings.length; i++) {
      assert.ok(
        standings[i - 1].points >= standings[i].points,
        `position ${i} should not have more points than position ${i - 1}`
      );
    }
  });

  it('champions have correct point calculation', () => {
    const standings = getStandings('brasileirao', 2023);
    if (standings.length > 0) {
      const first = standings[0];
      assert.equal(first.points, first.wins * 3 + first.draws);
    }
  });

  it('returns empty for non-existent season', () => {
    const standings = getStandings('brasileirao', 1900);
    assert.equal(standings.length, 0);
  });
});

// ── Statistical Analysis ─────────────────────────────────────────────

describe('Statistical Analysis', () => {
  it('returns biggest wins', () => {
    const wins = getBiggestWins(undefined, 10);
    assert.equal(wins.length, 10);
    // First should have largest goal difference
    const firstDiff = Math.abs(wins[0].homeGoal - wins[0].awayGoal);
    const lastDiff = Math.abs(wins[wins.length - 1].homeGoal - wins[wins.length - 1].awayGoal);
    assert.ok(firstDiff >= lastDiff, 'should be sorted by goal diff descending');
  });

  it('calculates average goals', () => {
    const stats = getAverageGoals('brasileirao');
    assert.ok(stats.avgGoalsPerMatch > 1 && stats.avgGoalsPerMatch < 5, `avg goals ${stats.avgGoalsPerMatch} should be realistic`);
    assert.ok(stats.totalMatches > 0);
  });

  it('returns home/away stats', () => {
    const stats = getHomeAwayStats('brasileirao');
    assert.equal(stats.homeWins + stats.awayWins + stats.draws, stats.totalMatches);
    assert.ok(stats.homeWinRate >= 0 && stats.homeWinRate <= 100);
  });

  it('returns top scoring teams', () => {
    const teams = getTopScoringTeams(undefined, undefined, 10);
    assert.equal(teams.length, 10);
    assert.ok(teams[0].goals >= teams[teams.length - 1].goals, 'sorted by goals desc');
  });

  it('returns best away records', () => {
    const teams = getTeamBestAwayRecord(5);
    assert.ok(teams.length > 0);
    assert.ok(teams[0].awayWinRate >= 0 && teams[0].awayWinRate <= 100);
  });
});

// ── Competition Info ─────────────────────────────────────────────────

describe('Competition Info', () => {
  it('lists available competitions', () => {
    const comps = getCompetitionList();
    assert.ok(comps.includes('brasileirao'));
    assert.ok(comps.includes('copa_do_brasil'));
    assert.ok(comps.includes('libertadores'));
  });

  it('lists seasons', () => {
    const seasons = getSeasonList();
    assert.ok(seasons.length > 0, 'should have seasons');
    assert.ok(seasons.includes(2023), 'should include 2023');
    // Sorted descending
    for (let i = 1; i < seasons.length; i++) {
      assert.ok(seasons[i - 1] >= seasons[i], 'seasons should be sorted descending');
    }
  });
});
