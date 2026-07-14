/**
 * Context
 * =======
 * Small hand-built in-memory fixtures for store/format unit tests.
 *
 * Using a tiny, fully-known dataset lets the behavioral tests assert exact
 * numbers (wins, points, goals, ordering) independent of the large real CSVs.
 * The real corpus is exercised separately in store.realdata.test.ts.
 */

import { canonicalTeam } from '../src/normalize.js';
import type { Match, Player } from '../src/types.js';

function match(
  competition: Match['competition'],
  date: string | undefined,
  season: number | undefined,
  home: string,
  away: string,
  hg: number,
  ag: number,
  round?: string,
): Match {
  return {
    competition,
    date,
    season,
    round,
    homeTeam: home,
    awayTeam: away,
    canonicalHome: canonicalTeam(home),
    canonicalAway: canonicalTeam(away),
    homeGoals: hg,
    awayGoals: ag,
    source: 'fixture',
  };
}

/**
 * A 3-team mini Brasileirão season (2023): A, B, C play a double round-robin
 * (6 matches). Known outcomes:
 *   A: beats B home (2-0) and away (1-0); draws C home (1-1); loses C away (0-2)
 *   => A: 2W 1D 1L, GF 4, GA 3, 7 pts
 *   B: loses to A twice; beats C home (3-1); draws C away (2-2)
 *   => B: 1W 1D 2L, GF 6, GA 6, 4 pts
 *   C: beats A away (2-0); draws A home (1-1); loses B away (1-3); draws B home (2-2)
 *   => C: 1W 2D 1L, GF 6, GA 7, 5 pts
 */
export const FIXTURE_MATCHES: Match[] = [
  match('Brasileirão Série A', '2023-04-01', 2023, 'Team A', 'Team B', 2, 0, 'Round 1'),
  match('Brasileirão Série A', '2023-04-08', 2023, 'Team B', 'Team A', 0, 1, 'Round 2'),
  match('Brasileirão Série A', '2023-04-15', 2023, 'Team A', 'Team C', 1, 1, 'Round 3'),
  match('Brasileirão Série A', '2023-04-22', 2023, 'Team C', 'Team A', 2, 0, 'Round 4'),
  match('Brasileirão Série A', '2023-04-29', 2023, 'Team B', 'Team C', 3, 1, 'Round 5'),
  match('Brasileirão Série A', '2023-05-06', 2023, 'Team C', 'Team B', 2, 2, 'Round 6'),
  // A cup match (different competition) and a different season to test filters.
  match('Copa do Brasil', '2023-06-01', 2023, 'Team A', 'Team C', 4, 0, 'Round 1'),
  match('Brasileirão Série A', '2022-04-01', 2022, 'Team A', 'Team B', 0, 5),
];

export const FIXTURE_PLAYERS: Player[] = [
  {
    id: 1,
    name: 'Alpha Silva',
    age: 25,
    nationality: 'Brazil',
    overall: 88,
    potential: 90,
    club: 'Team A',
    canonicalClub: canonicalTeam('Team A'),
    position: 'ST',
  },
  {
    id: 2,
    name: 'Beta Souza',
    age: 28,
    nationality: 'Brazil',
    overall: 82,
    potential: 82,
    club: 'Team B',
    canonicalClub: canonicalTeam('Team B'),
    position: 'GK',
  },
  {
    id: 3,
    name: 'Gamma Jones',
    age: 22,
    nationality: 'England',
    overall: 79,
    potential: 85,
    club: 'Team A',
    canonicalClub: canonicalTeam('Team A'),
    position: 'CM',
  },
];
