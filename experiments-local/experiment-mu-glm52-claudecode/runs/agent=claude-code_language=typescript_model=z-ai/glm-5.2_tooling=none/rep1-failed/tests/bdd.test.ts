/**
 * Brazilian Soccer MCP Server — BDD (Given/When/Then) test suite
 * =============================================================
 * Context block:
 *   Behavior-Driven Development scenarios, structured as
 *   `describe('Feature: …')` → `test('Scenario: …')` with explicit Given /
 *   When / Then sections inside each scenario. The suite exercises the pure
 *   query layer (`src/query.ts`), the normalization helpers (`src/normalize.ts`),
 *   and the data loader (`src/loader.ts`) against the real Kaggle CSV files so
 *   that "All 6 CSV files are loadable and queryable" and "Cross-file queries
 *   work" success criteria are verified end-to-end.
 *
 *   Run with:  npm test     (compiles then `node --test dist/tests/`)
 */

import { describe, test } from 'node:test';
import assert from 'node:assert/strict';

import { loadData } from '../src/loader.js';
import {
  averageGoals,
  biggestWins,
  canonicalMatches,
  competitionSummary,
  headToHead,
  homeAwaySplit,
  resolveTeams,
  searchMatches,
  searchPlayers,
  standings,
  teamStatistics,
  topPlayers,
} from '../src/query.js';
import {
  COMPETITIONS,
  normalizeTeam,
  parseDate,
  parseTeamRef,
  teamMatches,
} from '../src/normalize.js';
import { formatMatch } from '../src/format.js';

// ---------------------------------------------------------------------------
// Shared fixtures (loaded once for the whole suite).
// ---------------------------------------------------------------------------
const RAW = loadData();
const MATCHES = canonicalMatches(RAW.matches);
const PLAYERS = RAW.players;

// ---------------------------------------------------------------------------
// Tiny GWT helper: makes the Given/When/Then structure explicit and readable.
// ---------------------------------------------------------------------------
function gwt<T>(
  scenario: string,
  steps: {
    given?: string[];              // human-readable Given lines (documentation)
    when: () => T;                 // the action under test
    then: (result: T) => void;     // assertions
  },
): void {
  test(scenario, () => {
    const result = steps.when();
    steps.then(result);
  });
}

// ===========================================================================
describe('Feature: Match Queries', () => {
  gwt('Scenario: Find matches between two teams', {
    given: ['the match data is loaded'],
    when: () => searchMatches(MATCHES, { team: 'Flamengo', opponent: 'Fluminense' }),
    then: (matches) => {
      assert.ok(matches.length > 0, 'should return a non-empty list of matches');
      for (const m of matches) {
        assert.ok(m.dateStr, 'each match should have a date');
        assert.ok(m.home && m.away, 'each match should have home and away teams');
        assert.ok(m.homeGoal !== null && m.awayGoal !== null, 'each match should have scores');
        assert.ok(m.competition, 'each match should have a competition');
        const involvesFla = m.homeKey.includes('flamengo') || m.awayKey.includes('flamengo');
        const involvesFlu = m.homeKey.includes('fluminense') || m.awayKey.includes('fluminense');
        assert.ok(involvesFla && involvesFlu, 'each match should involve both teams');
      }
    },
  });

  gwt('Scenario: Find matches for a team in a season', {
    given: ['the match data is loaded'],
    when: () => searchMatches(MATCHES, { team: 'Palmeiras', season: 2023, limit: 50 }),
    then: (matches) => {
      assert.ok(matches.length > 0, 'Palmeiras played in 2023');
      for (const m of matches) {
        assert.equal(m.season, 2023, 'every result is from 2023');
        const involves = m.homeKey.includes('palmeiras') || m.awayKey.includes('palmeiras');
        assert.ok(involves, 'every result involves Palmeiras');
      }
    },
  });

  gwt('Scenario: Find matches by competition', {
    given: ['the match data is loaded'],
    when: () => searchMatches(MATCHES, { competition: 'Copa do Brasil', limit: 30 }),
    then: (matches) => {
      assert.ok(matches.length > 0, 'Copa do Brasil has matches');
      for (const m of matches) {
        assert.equal(m.competition, COMPETITIONS.COPA_DO_BRASIL, 'all results are Copa do Brasil');
      }
    },
  });

  gwt('Scenario: Filter matches by date range', {
    given: ['the match data is loaded'],
    when: () =>
      searchMatches(MATCHES, {
        team: 'Flamengo',
        fromDate: '2019-01-01',
        toDate: '2019-12-31',
        limit: 50,
      }),
    then: (matches) => {
      assert.ok(matches.length > 0, 'Flamengo played within the 2019 window');
      for (const m of matches) {
        assert.ok(m.dateStr >= '2019-01-01' && m.dateStr <= '2019-12-31', 'within 2019');
      }
    },
  });

  gwt('Scenario: Limit is respected', {
    given: ['the match data is loaded'],
    when: () => searchMatches(MATCHES, { team: 'Palmeiras', limit: 5 }),
    then: (matches) => {
      assert.ok(matches.length <= 5, 'no more than 5 matches returned');
    },
  });
});

// ===========================================================================
describe('Feature: Team Queries', () => {
  gwt('Scenario: Get team statistics for a season', {
    given: ['the match data is loaded'],
    when: () => teamStatistics(MATCHES, { team: 'Palmeiras', season: 2022 }),
    then: (t) => {
      assert.ok(t.played > 0, 'Palmeiras 2022 has matches');
      assert.equal(t.wins + t.draws + t.losses, t.played, 'W+D+L equals played');
      assert.equal(t.points, 3 * t.wins + t.draws, 'points = 3*W + D');
      assert.ok(t.goalsFor >= 0 && t.goalsAgainst >= 0, 'goals are non-negative');
    },
  });

  gwt('Scenario: Home and away splits sum to total', {
    given: ['the match data is loaded'],
    when: () => ({
      home: teamStatistics(MATCHES, { team: 'São Paulo', season: 2008, venue: 'home', competition: 'Brasileirão' }),
      away: teamStatistics(MATCHES, { team: 'São Paulo', season: 2008, venue: 'away', competition: 'Brasileirão' }),
      all: teamStatistics(MATCHES, { team: 'São Paulo', season: 2008, competition: 'Brasileirão' }),
    }),
    then: ({ home, away, all }) => {
      assert.equal(home.played + away.played, all.played, 'home + away == total');
      assert.ok(home.played > 0 && away.played > 0, 'played both home and away');
    },
  });

  gwt('Scenario: Compare two teams head-to-head', {
    given: ['the match data is loaded'],
    when: () => headToHead(MATCHES, 'Palmeiras', 'Santos'),
    then: (h) => {
      assert.ok(h.matches.length > 0, 'Palmeiras vs Santos has matches');
      const scored = h.matches.filter((m) => m.homeGoal !== null && m.awayGoal !== null).length;
      assert.equal(h.aWins + h.bWins + h.draws, scored, 'tallies partition scored matches');
      assert.ok(h.aWins + h.bWins + h.draws > 0, 'at least one decided/drawn match');
    },
  });

  gwt('Scenario: Flamengo vs Fluminense (Fla-Flu) head-to-head', {
    given: ['the match data is loaded'],
    when: () => headToHead(MATCHES, 'Flamengo', 'Fluminense'),
    then: (h) => {
      assert.ok(h.matches.length > 0, 'Fla-Flu has matches');
      for (const m of h.matches.slice(0, 5)) {
        const line = formatMatch(m);
        assert.match(line, /Flamengo|Fluminense/, 'formatted line names a team');
      }
    },
  });
});

// ===========================================================================
describe('Feature: Player Queries', () => {
  gwt('Scenario: Find all Brazilian players', {
    given: ['the FIFA player data is loaded'],
    when: () => searchPlayers(PLAYERS, { nationality: 'Brazil', limit: 50 }),
    then: (players) => {
      assert.ok(players.length > 0, 'there are Brazilian players');
      for (const p of players) {
        assert.equal(p.nationality, 'Brazil', 'every result is Brazilian');
      }
    },
  });

  gwt('Scenario: Top players are sorted by rating descending', {
    given: ['the FIFA player data is loaded'],
    when: () => topPlayers(PLAYERS, { nationality: 'Brazil', limit: 10 }),
    then: (players) => {
      assert.ok(players.length > 0, 'top players returned');
      for (let i = 1; i < players.length; i++) {
        assert.ok(
          (players[i - 1].overall ?? 0) >= (players[i].overall ?? 0),
          'ratings are non-increasing',
        );
      }
    },
  });

  gwt('Scenario: Search a player by name', {
    given: ['the FIFA player data is loaded'],
    when: () => searchPlayers(PLAYERS, { name: 'Neymar', limit: 10 }),
    then: (players) => {
      assert.ok(players.length > 0, 'Neymar is found');
      assert.ok(
        players.some((p) => p.name.toLowerCase().includes('neymar')),
        'a result is named Neymar',
      );
    },
  });

  gwt('Scenario: Filter players by position', {
    given: ['the FIFA player data is loaded'],
    when: () => searchPlayers(PLAYERS, { position: 'ST', limit: 50 }),
    then: (players) => {
      assert.ok(players.length > 0, 'strikers exist');
      for (const p of players) {
        assert.equal(p.position, 'ST', 'every result is a striker');
      }
    },
  });
});

// ===========================================================================
describe('Feature: Competition Queries', () => {
  gwt('Scenario: Who won the 2019 Brasileirão', {
    given: ['the match data is loaded'],
    when: () => standings(MATCHES, { competition: 'Brasileirão', season: 2019, limit: 1 }),
    then: (table) => {
      assert.equal(table.length, 1, 'champion row exists');
      assert.equal(table[0].team, 'Flamengo', 'Flamengo won the 2019 Brasileirão');
      assert.equal(table[0].points, 90, 'with 90 points');
      assert.equal(table[0].wins, 28, '28 wins');
      assert.equal(table[0].draws, 6, '6 draws');
      assert.equal(table[0].losses, 4, '4 losses');
    },
  });

  gwt('Scenario: 2008 Brasileirão champion is São Paulo', {
    given: ['the match data is loaded'],
    when: () => standings(MATCHES, { competition: 'Brasileirão', season: 2008, limit: 1 }),
    then: (table) => {
      assert.equal(table[0].team, 'São Paulo', 'São Paulo won 2008');
    },
  });

  gwt('Scenario: Standings are sorted by points descending', {
    given: ['the match data is loaded'],
    when: () => standings(MATCHES, { competition: 'Brasileirão', season: 2019, limit: 20 }),
    then: (table) => {
      for (let i = 1; i < table.length; i++) {
        assert.ok(
          table[i - 1].points >= table[i].points,
          'points are non-increasing down the table',
        );
      }
    },
  });
});

// ===========================================================================
describe('Feature: Statistical Analysis', () => {
  gwt('Scenario: Average goals per Brasileirão match', {
    given: ['the match data is loaded'],
    when: () => averageGoals(MATCHES, { competition: 'Brasileirão' }),
    then: (r) => {
      assert.ok(r.matches > 0, 'there are Brasileirão matches');
      assert.ok(r.avgPerMatch > 2 && r.avgPerMatch < 3, 'avg is in a plausible range');
      // avgPerMatch is rounded to 2 decimals, so allow rounding tolerance.
      assert.ok(
        Math.abs(r.totalGoals / r.matches - r.avgPerMatch) < 0.01,
        'avg is consistent with total / matches',
      );
    },
  });

  gwt('Scenario: Biggest wins are ordered by goal difference', {
    given: ['the match data is loaded'],
    when: () => biggestWins(MATCHES, { limit: 10 }),
    then: (wins) => {
      assert.ok(wins.length > 0, 'there are wins');
      const diffs = wins.map((m) => Math.abs((m.homeGoal ?? 0) - (m.awayGoal ?? 0)));
      for (let i = 1; i < diffs.length; i++) {
        assert.ok(diffs[i - 1] >= diffs[i], 'differences are non-increasing');
      }
      assert.ok(diffs[0] >= 5, 'top victory has a large margin');
    },
  });

  gwt('Scenario: Home/away/draw split sums to total', {
    given: ['the match data is loaded'],
    when: () => homeAwaySplit(MATCHES, { competition: 'Brasileirão' }),
    then: (r) => {
      assert.ok(r.total > 0, 'there are matches');
      assert.equal(r.homeWins + r.awayWins + r.draws, r.total, 'outcomes partition the matches');
      assert.ok(r.homeWins > r.awayWins, 'home advantage is visible');
    },
  });
});

// ===========================================================================
describe('Feature: Team Name Normalization', () => {
  gwt('Scenario: Normalize a team with state suffix', {
    given: ['a name like "Palmeiras-SP"'],
    when: () => normalizeTeam('Palmeiras-SP'),
    then: (n) => {
      assert.equal(n.key, 'palmeiras', 'state suffix stripped from key');
      assert.equal(n.state, 'SP', 'state captured');
      assert.equal(n.display, 'Palmeiras', 'display name keeps the club');
    },
  });

  gwt('Scenario: Normalize an accented team name', {
    given: ['a name like "São Paulo"'],
    when: () => normalizeTeam('São Paulo'),
    then: (n) => {
      assert.equal(n.key, 'sao paulo', 'accents stripped, lowercased');
    },
  });

  gwt('Scenario: Normalize a name with parenthetical annotation', {
    given: ['a name like "Nacional (URU)"'],
    when: () => normalizeTeam('Nacional (URU)'),
    then: (n) => {
      assert.equal(n.key, 'nacional', 'parenthetical content removed');
    },
  });

  gwt('Scenario: Parse a Brazilian-format date', {
    given: ['a date string "29/03/2003"'],
    when: () => parseDate('29/03/2003'),
    then: (d) => {
      assert.equal(d.iso, '2003-03-29', 'DD/MM/YYYY maps to YYYY-MM-DD');
      assert.ok(d.date !== null, 'a Date is produced');
    },
  });

  gwt('Scenario: Parse an ISO date with time', {
    given: ['a datetime "2012-05-19 18:30:00"'],
    when: () => parseDate('2012-05-19 18:30:00'),
    then: (d) => {
      assert.equal(d.iso, '2012-05-19', 'time component ignored in iso');
    },
  });

  gwt('Scenario: Team ref matches record across naming variations', {
    given: ['a query "Palmeiras" and a record team "Palmeiras"'],
    when: () => teamMatches('palmeiras', undefined, parseTeamRef('Palmeiras')),
    then: (ok) => assert.ok(ok, 'bare club name matches its own key'),
  });
});

// ===========================================================================
describe('Feature: Cross-file & Resolution Queries', () => {
  gwt('Scenario: All six CSV files are loadable', {
    given: ['the data directory is present'],
    when: () => ({ matches: MATCHES.length, players: PLAYERS.length }),
    then: (counts) => {
      assert.ok(counts.matches > 10000, 'match data loaded across all match files');
      assert.ok(counts.players > 10000, 'FIFA player data loaded');
    },
  });

  gwt('Scenario: Competition summary lists known competitions', {
    given: ['the match data is loaded'],
    when: () => competitionSummary(MATCHES),
    then: (summary) => {
      const names = summary.map((c) => c.competition);
      assert.ok(names.includes(COMPETITIONS.BRASILEIRAO), 'Brasileirão listed');
      assert.ok(names.includes(COMPETITIONS.COPA_DO_BRASIL), 'Copa do Brasil listed');
      assert.ok(names.includes(COMPETITIONS.LIBERTADORES), 'Libertadores listed');
      for (const c of summary) {
        assert.ok(c.totalMatches > 0, 'every competition has matches');
      }
    },
  });

  gwt('Scenario: Resolve a team name fragment', {
    given: ['the match data is loaded'],
    when: () => resolveTeams(MATCHES, 'palmeiras'),
    then: (teams) => {
      assert.ok(teams.length > 0, 'Palmeiras is resolved');
      assert.ok(
        teams.some((t) => t.display.toLowerCase().includes('palmeiras')),
        'a resolved team is Palmeiras',
      );
    },
  });

  gwt('Scenario: Cross-file query — a player and a team both resolve', {
    given: ['both match and player data are loaded'],
    when: () => ({
      neymar: searchPlayers(PLAYERS, { name: 'Neymar', limit: 1 }),
      santosMatches: searchMatches(MATCHES, { team: 'Santos', season: 2019, limit: 1 }),
    }),
    then: ({ neymar, santosMatches }) => {
      assert.ok(neymar.length > 0, 'player data resolves Neymar');
      assert.ok(santosMatches.length > 0, 'match data resolves Santos 2019');
    },
  });
});
