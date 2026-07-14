import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import { getDatabase, resetDatabase } from '../data-loader.js';
import {
  biggestWins,
  buildTeamRecord,
  competitionOverview,
  computeStandings,
  filterMatches,
  filterPlayers,
  headToHead,
  highScoringMatches,
  rankTeams,
  resolveCompetition,
} from '../query-engine.js';
import type { Database } from '../types.js';

let db: Database;

beforeAll(() => {
  db = getDatabase();
});

afterEach(() => {
  // Don't reset here — expensive reload between tests; reset only in data-loader tests
});

// ---------------------------------------------------------------------------
// resolveCompetition
// ---------------------------------------------------------------------------

describe('resolveCompetition', () => {
  it('resolves Brasileirão variants', () => {
    expect(resolveCompetition('brasileirao')).toBe('Brasileirão Serie A');
    expect(resolveCompetition('Brasileirão')).toBe('Brasileirão Serie A');
    expect(resolveCompetition('serie a')).toBe('Brasileirão Serie A');
  });

  it('resolves Copa do Brasil', () => {
    expect(resolveCompetition('copa brasil')).toBe('Copa do Brasil');
    expect(resolveCompetition('copa do brasil')).toBe('Copa do Brasil');
  });

  it('resolves Copa Libertadores', () => {
    expect(resolveCompetition('libertadores')).toBe('Copa Libertadores');
    expect(resolveCompetition('copa libertadores')).toBe('Copa Libertadores');
  });

  it('returns null for unknown competition', () => {
    expect(resolveCompetition('unknown')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// filterMatches
// ---------------------------------------------------------------------------

describe('filterMatches', () => {
  it('returns all matches without filter', () => {
    const result = filterMatches(db.matches, {});
    expect(result.length).toBe(db.matches.length);
  });

  it('filters by team name', () => {
    const result = filterMatches(db.matches, { team: 'Flamengo' });
    expect(result.length).toBeGreaterThan(100);
    for (const m of result) {
      const involved =
        m.homeTeamNormalized.toLowerCase().includes('flamengo') ||
        m.awayTeamNormalized.toLowerCase().includes('flamengo') ||
        m.homeTeam.toLowerCase().includes('flamengo') ||
        m.awayTeam.toLowerCase().includes('flamengo');
      expect(involved).toBe(true);
    }
  });

  it('filters by season', () => {
    const result = filterMatches(db.matches, { season: 2019 });
    for (const m of result) {
      expect(m.season).toBe(2019);
    }
    expect(result.length).toBeGreaterThan(0);
  });

  it('filters by competition', () => {
    const result = filterMatches(db.matches, { competition: 'libertadores' });
    for (const m of result) {
      expect(m.competition).toBe('Copa Libertadores');
    }
    expect(result.length).toBeGreaterThan(1000);
  });

  it('filters by date range', () => {
    const result = filterMatches(db.matches, { dateFrom: '2019-01-01', dateTo: '2019-12-31' });
    for (const m of result) {
      expect(m.date >= '2019-01-01').toBe(true);
      expect(m.date <= '2019-12-31').toBe(true);
    }
  });

  it('filters home matches only', () => {
    const result = filterMatches(db.matches, { team: 'Palmeiras', venue: 'home' });
    for (const m of result) {
      const homeMatch =
        m.homeTeamNormalized.toLowerCase().includes('palmeiras') ||
        m.homeTeam.toLowerCase().includes('palmeiras');
      expect(homeMatch).toBe(true);
    }
  });

  it('filters by team + opponent for head-to-head', () => {
    const result = filterMatches(db.matches, { team: 'Flamengo', opponent: 'Fluminense' });
    expect(result.length).toBeGreaterThan(5);
    for (const m of result) {
      const hasFlamengo =
        m.homeTeamNormalized.toLowerCase().includes('flamengo') ||
        m.awayTeamNormalized.toLowerCase().includes('flamengo') ||
        m.homeTeam.toLowerCase().includes('flamengo') ||
        m.awayTeam.toLowerCase().includes('flamengo');
      const hasFluminense =
        m.homeTeamNormalized.toLowerCase().includes('fluminense') ||
        m.awayTeamNormalized.toLowerCase().includes('fluminense') ||
        m.homeTeam.toLowerCase().includes('fluminense') ||
        m.awayTeam.toLowerCase().includes('fluminense');
      expect(hasFlamengo).toBe(true);
      expect(hasFluminense).toBe(true);
    }
  });

  it('returns results sorted newest-first', () => {
    const result = filterMatches(db.matches, { team: 'Corinthians', competition: 'brasileirao' });
    for (let i = 1; i < Math.min(result.length, 50); i++) {
      expect(result[i - 1]!.date >= result[i]!.date).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// buildTeamRecord
// ---------------------------------------------------------------------------

describe('buildTeamRecord', () => {
  it('calculates correct W/D/L for Flamengo in 2019', () => {
    const season2019 = filterMatches(db.matches, {
      team: 'Flamengo',
      competition: 'brasileirao',
      season: 2019,
    });
    expect(season2019.length).toBeGreaterThan(0);
    const rec = buildTeamRecord('Flamengo', season2019);
    expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
    expect(rec.points).toBe(rec.wins * 3 + rec.draws);
    expect(rec.goalsFor).toBeGreaterThan(0);
    // Flamengo 2019 were champions — should have strong record
    expect(rec.wins).toBeGreaterThan(rec.losses);
  });

  it('goal diff equals goalsFor minus goalsAgainst', () => {
    const matches = filterMatches(db.matches, { team: 'Santos', season: 2022 });
    const rec = buildTeamRecord('Santos', matches);
    expect(rec.goalDiff).toBe(rec.goalsFor - rec.goalsAgainst);
  });

  it('win rate is wins / matches', () => {
    const matches = filterMatches(db.matches, { team: 'Palmeiras', season: 2022 });
    const rec = buildTeamRecord('Palmeiras', matches);
    if (rec.matches > 0) {
      expect(rec.winRate).toBeCloseTo(rec.wins / rec.matches, 5);
    }
  });

  it('returns zero stats for empty match list', () => {
    const rec = buildTeamRecord('NonExistentTeam', []);
    expect(rec.matches).toBe(0);
    expect(rec.wins).toBe(0);
    expect(rec.points).toBe(0);
    expect(rec.winRate).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// computeStandings
// ---------------------------------------------------------------------------

describe('computeStandings', () => {
  it('returns teams sorted by points descending', () => {
    const matches = db.matches.filter(
      (m) => m.source === 'brasileirao' && m.season === 2022
    );
    const table = computeStandings(matches);
    for (let i = 1; i < table.length; i++) {
      expect(table[i - 1]!.points >= table[i]!.points).toBe(true);
    }
  });

  it('top team in 2019 Brasileirão is Flamengo-RJ', () => {
    const matches = db.matches.filter(
      (m) => m.source === 'brasileirao' && m.season === 2019
    );
    const table = computeStandings(matches);
    expect(table.length).toBeGreaterThan(15);
    // Flamengo won 2019 with 90 pts — stored as "Flamengo-RJ" in this dataset
    expect(table[0]!.team).toBe('Flamengo-RJ');
  });
});

// ---------------------------------------------------------------------------
// headToHead
// ---------------------------------------------------------------------------

describe('headToHead', () => {
  it('returns symmetric results regardless of team order', () => {
    const h1 = headToHead(db.matches, 'Flamengo', 'Fluminense');
    const h2 = headToHead(db.matches, 'Fluminense', 'Flamengo');
    expect(h1.matches.length).toBe(h2.matches.length);
    expect(h1.team1Wins).toBe(h2.team2Wins);
    expect(h1.team2Wins).toBe(h2.team1Wins);
    expect(h1.draws).toBe(h2.draws);
  });

  it('returns empty result for non-existent matchup', () => {
    const result = headToHead(db.matches, 'TeamXYZ_NoExist', 'TeamABC_NoExist');
    expect(result.matches.length).toBe(0);
    expect(result.team1Wins).toBe(0);
    expect(result.team2Wins).toBe(0);
  });

  it('goal totals match sum across all matches', () => {
    const h2h = headToHead(db.matches, 'Palmeiras', 'Santos');
    let t1G = 0, t2G = 0;
    for (const m of h2h.matches) {
      const palmeiraIsHome =
        m.homeTeamNormalized.toLowerCase().includes('palmeiras') ||
        m.homeTeam.toLowerCase().includes('palmeiras');
      t1G += palmeiraIsHome ? m.homeGoals : m.awayGoals;
      t2G += palmeiraIsHome ? m.awayGoals : m.homeGoals;
    }
    expect(h2h.team1Goals).toBe(t1G);
    expect(h2h.team2Goals).toBe(t2G);
  });
});

// ---------------------------------------------------------------------------
// filterPlayers
// ---------------------------------------------------------------------------

describe('filterPlayers', () => {
  it('filters by nationality', () => {
    const brazilians = filterPlayers(db.players, { nationality: 'Brazil' });
    expect(brazilians.length).toBeGreaterThan(500);
    for (const p of brazilians.slice(0, 20)) {
      expect(p.nationality).toBe('Brazil');
    }
  });

  it('filters by name (partial, case-insensitive)', () => {
    const result = filterPlayers(db.players, { name: 'neymar' });
    expect(result.length).toBeGreaterThan(0);
    expect(result.some((p) => p.name.toLowerCase().includes('neymar'))).toBe(true);
  });

  it('filters by club (partial match)', () => {
    // The FIFA dataset uses full Brazilian club names; Santos is present
    const result = filterPlayers(db.players, { club: 'Santos' });
    expect(result.length).toBeGreaterThan(0);
    for (const p of result) {
      expect((p.club ?? '').toLowerCase()).toContain('santos');
    }
  });

  it('filters by position', () => {
    const gks = filterPlayers(db.players, { position: 'GK' });
    expect(gks.length).toBeGreaterThan(100);
    for (const p of gks.slice(0, 20)) {
      expect(p.position).toBe('GK');
    }
  });

  it('filters by minimum overall rating', () => {
    const elite = filterPlayers(db.players, { minOverall: 90 });
    expect(elite.length).toBeGreaterThan(0);
    for (const p of elite) {
      expect(p.overall ?? 0).toBeGreaterThanOrEqual(90);
    }
  });

  it('filters by max overall rating', () => {
    const low = filterPlayers(db.players, { maxOverall: 60 });
    expect(low.length).toBeGreaterThan(0);
    for (const p of low.slice(0, 50)) {
      expect(p.overall ?? 100).toBeLessThanOrEqual(60);
    }
  });

  it('returns empty list when no match', () => {
    const result = filterPlayers(db.players, { name: 'xyzxyzxyz_definitely_not_a_player' });
    expect(result.length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Aggregate stats
// ---------------------------------------------------------------------------

describe('competitionOverview', () => {
  it('returns correct totals', () => {
    const matches = db.matches.filter((m) => m.source === 'brasileirao' && m.season === 2022);
    const ov = competitionOverview(matches);
    expect(ov.totalMatches).toBe(matches.length);
    expect(ov.homeWins + ov.awayWins + ov.draws).toBe(matches.length);
    expect(ov.avgGoalsPerMatch).toBeGreaterThan(0);
  });
});

describe('biggestWins', () => {
  it('returns matches sorted by margin descending', () => {
    const top10 = biggestWins(db.matches, 10);
    expect(top10.length).toBe(10);
    for (let i = 1; i < top10.length; i++) {
      const prevMargin = Math.abs(top10[i - 1]!.homeGoals - top10[i - 1]!.awayGoals);
      const currMargin = Math.abs(top10[i]!.homeGoals - top10[i]!.awayGoals);
      expect(prevMargin >= currMargin).toBe(true);
    }
  });

  it('excludes draws', () => {
    const top = biggestWins(db.matches, 20);
    for (const m of top) {
      expect(m.homeGoals).not.toBe(m.awayGoals);
    }
  });
});

describe('highScoringMatches', () => {
  it('returns matches sorted by total goals descending', () => {
    const top5 = highScoringMatches(db.matches, 5);
    expect(top5.length).toBe(5);
    for (let i = 1; i < top5.length; i++) {
      const prevTotal = top5[i - 1]!.homeGoals + top5[i - 1]!.awayGoals;
      const currTotal = top5[i]!.homeGoals + top5[i]!.awayGoals;
      expect(prevTotal >= currTotal).toBe(true);
    }
  });
});

describe('rankTeams', () => {
  it('returns teams ranked by points', () => {
    const matches = db.matches.filter((m) => m.source === 'brasileirao' && m.season === 2022);
    const ranked = rankTeams(matches, 'points', 5);
    expect(ranked.length).toBe(5);
    for (let i = 1; i < ranked.length; i++) {
      expect(ranked[i - 1]!.points >= ranked[i]!.points).toBe(true);
    }
  });

  it('returns teams ranked by goals scored', () => {
    const matches = db.matches.filter((m) => m.source === 'brasileirao' && m.season === 2022);
    const ranked = rankTeams(matches, 'goals_for', 5);
    for (let i = 1; i < ranked.length; i++) {
      expect(ranked[i - 1]!.goalsFor >= ranked[i]!.goalsFor).toBe(true);
    }
  });
});
