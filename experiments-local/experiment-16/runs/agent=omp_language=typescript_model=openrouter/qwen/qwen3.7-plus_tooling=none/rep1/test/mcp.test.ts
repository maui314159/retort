import { describe, it, expect, beforeAll } from 'vitest';
import { loadMatches, loadPlayers, normalizeTeamName } from '../src/data';

describe('Data Loading', () => {
  it('should load matches from all datasets', async () => {
    const matches = await loadMatches();
    expect(matches.length).toBeGreaterThan(1000);
    
    const competitions = new Set(matches.map(m => m.competition));
    expect(competitions.has('Brasileirão')).toBe(true);
    expect(competitions.has('Copa do Brasil')).toBe(true);
    expect(competitions.has('Copa Libertadores')).toBe(true);
  });

  it('should load players from FIFA dataset', async () => {
    const players = await loadPlayers();
    expect(players.length).toBeGreaterThan(10000);
    
    const brazilianPlayers = players.filter(p => p.nationality === 'Brazil');
    expect(brazilianPlayers.length).toBeGreaterThan(100);
  });
});

describe('Team Name Normalization', () => {
  it('should normalize team names with state codes', () => {
    expect(normalizeTeamName('Palmeiras-SP')).toBe('palmeiras');
    expect(normalizeTeamName('Flamengo - RJ')).toBe('flamengo');
  });

  it('should normalize full club names', () => {
    expect(normalizeTeamName('Sport Club Corinthians Paulista')).toBe('corinthians');
    expect(normalizeTeamName('CR Flamengo')).toBe('flamengo');
    expect(normalizeTeamName('SE Palmeiras')).toBe('palmeiras');
  });

  it('should handle parentheticals', () => {
    expect(normalizeTeamName('Boavista Sport Club (antigo Esporte Clube Barreira) - RJ')).toBe('boavista');
  });
});

describe('BDD Test Scenarios', () => {
  let matches: Awaited<ReturnType<typeof loadMatches>>;

  beforeAll(async () => {
    matches = await loadMatches();
  });

  it('Feature: Match Queries - Scenario: Find matches between two teams', () => {
    const team1 = 'flamengo';
    const team2 = 'fluminense';
    
    const h2hMatches = matches.filter(m => {
      const home = normalizeTeamName(m.homeTeam);
      const away = normalizeTeamName(m.awayTeam);
      return (home.includes(team1) && away.includes(team2)) || (home.includes(team2) && away.includes(team1));
    });

    expect(h2hMatches.length).toBeGreaterThan(0);
    expect(h2hMatches[0]).toHaveProperty('date');
    expect(h2hMatches[0]).toHaveProperty('homeGoals');
    expect(h2hMatches[0]).toHaveProperty('awayGoals');
    expect(h2hMatches[0]).toHaveProperty('competition');
  });

  it('Feature: Team Queries - Scenario: Get team statistics', () => {
    const teamSearch = 'palmeiras';
    const season = 2023;
    
    const teamMatches = matches.filter(m => m.season === season && (
      normalizeTeamName(m.homeTeam).includes(teamSearch) || 
      normalizeTeamName(m.awayTeam).includes(teamSearch)
    ));

    expect(teamMatches.length).toBeGreaterThan(0);
    
    let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
    for (const m of teamMatches) {
      const isHome = normalizeTeamName(m.homeTeam).includes(teamSearch);
      const teamGoals = isHome ? m.homeGoals : m.awayGoals;
      const oppGoals = isHome ? m.awayGoals : m.homeGoals;
      
      goalsFor += teamGoals;
      goalsAgainst += oppGoals;
      
      if (teamGoals > oppGoals) wins++;
      else if (teamGoals === oppGoals) draws++;
      else losses++;
    }

    expect(wins + draws + losses).toBe(teamMatches.length);
    expect(goalsFor).toBeGreaterThan(0);
  });
});