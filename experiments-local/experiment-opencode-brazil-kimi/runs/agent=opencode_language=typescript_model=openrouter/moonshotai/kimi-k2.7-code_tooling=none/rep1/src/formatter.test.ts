/*
 * Brazilian Soccer MCP Server - Formatter unit tests
 */

import {
  formatMatches,
  formatHeadToHead,
  formatTeamRecord,
  formatStandings,
  formatPlayers,
  formatBiggestWins,
  formatAverageGoals,
  formatHomeWinRate
} from './formatter.js';
import { Match, Player, Standing, TeamRecord, HeadToHead } from './types.js';

describe('Formatter', () => {
  const match: Match = {
    datetime: new Date('2023-09-03T16:00:00'),
    date: '2023-09-03',
    season: 2023,
    competition: 'Brasileirão',
    round: '22',
    homeTeam: 'Flamengo',
    awayTeam: 'Fluminense',
    homeGoal: 2,
    awayGoal: 1,
    source: 'test'
  };

  it('formats a list of matches', () => {
    const text = formatMatches([match]);
    expect(text).toContain('2023-09-03');
    expect(text).toContain('Flamengo');
    expect(text).toContain('2-1');
    expect(text).toContain('Fluminense');
    expect(text).toContain('Brasileirão');
  });

  it('formats head-to-head summaries', () => {
    const h2h: HeadToHead = {
      teamA: 'Flamengo',
      teamB: 'Fluminense',
      teamAWins: 12,
      teamBWins: 8,
      draws: 7,
      teamAGoals: 35,
      teamBGoals: 28,
      matches: [match]
    };
    const text = formatHeadToHead(h2h);
    expect(text).toContain('Flamengo vs Fluminense');
    expect(text).toContain('Flamengo 12 wins, Fluminense 8 wins, 7 draws');
  });

  it('formats team records', () => {
    const record: TeamRecord = {
      team: 'Corinthians',
      matches: 19,
      wins: 11,
      draws: 5,
      losses: 3,
      goalsFor: 28,
      goalsAgainst: 15,
      points: 38
    };
    const text = formatTeamRecord(record, 'Corinthians home record (2022 Brasileirão)');
    expect(text).toContain('Matches: 19');
    expect(text).toContain('Win rate: 57.9%');
  });

  it('formats standings', () => {
    const standings: Standing[] = [
      {
        team: 'Flamengo',
        matches: 38,
        wins: 28,
        draws: 6,
        losses: 4,
        goalsFor: 86,
        goalsAgainst: 37,
        points: 90,
        goalDifference: 49,
        position: 1
      }
    ];
    const text = formatStandings(standings, '2019 Brasileirão');
    expect(text).toContain('Flamengo');
    expect(text).toContain('90 pts');
    expect(text).toContain('Champion');
  });

  it('formats player rankings', () => {
    const players: Player[] = [
      { name: 'Neymar Jr', nationality: 'Brazil', overall: 92, position: 'LW', club: 'Paris Saint-Germain', source: 'test' }
    ];
    const text = formatPlayers(players, 'Top Brazilian players');
    expect(text).toContain('Neymar Jr');
    expect(text).toContain('Overall: 92');
  });

  it('formats average goals and home win rate', () => {
    expect(formatAverageGoals(2.47)).toContain('2.47');
    expect(formatHomeWinRate(0.473)).toContain('47.3%');
  });
});
