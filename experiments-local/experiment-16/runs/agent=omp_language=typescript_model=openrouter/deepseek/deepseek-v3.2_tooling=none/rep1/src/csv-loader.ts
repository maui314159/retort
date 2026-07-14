/**
 * Brazilian Soccer MCP Server - CSV Loading Utilities
 * 
 * Loads and parses soccer datasets from CSV files with proper type handling
 * and date format normalization.
 */

import { readFileSync } from 'fs';
import { parse } from 'papaparse';
import { parse as parseDate, isValid, parseISO } from 'date-fns';
import { Match, Player, DatasetType } from './types';

/**
 * Normalizes team names by removing state suffixes and standardizing variations
 */
export function normalizeTeamName(teamName: string): string {
  if (!teamName || typeof teamName !== 'string') return '';
  
  const trimmed = teamName.trim();
  
  // Remove state suffix (e.g., "Palmeiras-SP" → "Palmeiras")
  const withoutSuffix = trimmed.replace(/-\s*[A-Z]{2}$/, '');
  
  // Handle common Brazilian club naming variations
  const variations: Record<string, string> = {
    'Sport Club Corinthians Paulista': 'Corinthians',
    'Corinthians-SP': 'Corinthians',
    'Corinthians Paulista': 'Corinthians',
    'Sociedade Esportiva Palmeiras': 'Palmeiras',
    'Palmeiras-SP': 'Palmeiras',
    'Clube de Regatas do Flamengo': 'Flamengo',
    'Flamengo-RJ': 'Flamengo',
    'São Paulo Futebol Clube': 'São Paulo',
    'São Paulo-SP': 'São Paulo',
    'Sao Paulo': 'São Paulo',
    'Grêmio Foot-Ball Porto Alegrense': 'Grêmio',
    'Gremio-RS': 'Grêmio',
    'Sport Club Internacional': 'Internacional',
    'Internacional-RS': 'Internacional',
    'Santos Futebol Clube': 'Santos',
    'Santos-SP': 'Santos',
    'Clube Atlético Mineiro': 'Atlético-MG',
    'Atletico-MG': 'Atlético-MG',
    'Cruzeiro Esporte Clube': 'Cruzeiro',
    'Cruzeiro-MG': 'Cruzeiro',
    'Fluminense Football Club': 'Fluminense',
    'Fluminense-RJ': 'Fluminense',
    'Botafogo de Futebol e Regatas': 'Botafogo',
    'Botafogo-RJ': 'Botafogo',
    'Vasco da Gama': 'Vasco',
    'Vasco da Gama-RJ': 'Vasco',
  };
  
  return variations[trimmed] || variations[withoutSuffix] || withoutSuffix || trimmed;
}

/**
 * Parses various date formats found in the datasets
 */
export function parseSoccerDate(dateStr: string): Date {
  if (!dateStr || typeof dateStr !== 'string') return new Date(NaN);
  
  const trimmed = dateStr.trim();
  
  // Try ISO format first (e.g., "2023-09-24")
  const isoDate = parseISO(trimmed);
  if (isValid(isoDate)) return isoDate;
  
  // Try Brazilian format (e.g., "29/03/2003")
  const brDate = parseDate(trimmed, 'dd/MM/yyyy', new Date());
  if (isValid(brDate)) return brDate;
  
  // Try with time component (e.g., "2012-05-19 18:30:00")
  const dateTime = parseDate(trimmed, 'yyyy-MM-dd HH:mm:ss', new Date());
  if (isValid(dateTime)) return dateTime;
  
  // Try just date part of datetime
  const datePart = trimmed.split(' ')[0];
  const dateOnly = parseISO(datePart) || parseDate(datePart, 'dd/MM/yyyy', new Date());
  if (isValid(dateOnly)) return dateOnly;
  
  // Fallback to JS Date parsing
  const fallback = new Date(trimmed);
  return isValid(fallback) ? fallback : new Date(NaN);
}

/**
 * Extracts season/year from date or explicit season field
 */
export function extractSeason(date: Date, seasonField?: string | number): number {
  if (seasonField !== undefined) {
    const num = Number(seasonField);
    if (!isNaN(num) && num > 1900 && num < 2100) return num;
  }
  
  if (isValid(date)) {
    return date.getFullYear();
  }
  
  return new Date().getFullYear();
}

/**
 * Loads and parses Brasileirão Serie A matches
 */
export function loadBrasileiraoMatches(filePath: string): Match[] {
  const content = readFileSync(filePath, 'utf-8');
  const result = parse<{
    datetime: string;
    home_team: string;
    home_team_state: string;
    away_team: string;
    away_team_state: string;
    home_goal: string;
    away_goal: string;
    season: string;
    round: string;
  }>(content, { header: true, skipEmptyLines: true });
  
  return result.data
    .filter(row => row.datetime && row.home_team && row.away_team)
    .map(row => {
      const date = parseSoccerDate(row.datetime);
      const homeGoals = Number(row.home_goal) || 0;
      const awayGoals = Number(row.away_goal) || 0;
      
      return {
        date,
        homeTeam: normalizeTeamName(row.home_team),
        awayTeam: normalizeTeamName(row.away_team),
        homeGoals,
        awayGoals,
        season: extractSeason(date, row.season),
        round: Number(row.round) || row.round,
        competition: 'Brasileirão Serie A',
        source: 'brasileirao',
        originalData: { ...row }
      };
    });
}

/**
 * Loads and parses Copa do Brasil matches
 */
export function loadCopaDoBrasilMatches(filePath: string): Match[] {
  const content = readFileSync(filePath, 'utf-8');
  const result = parse<{
    round: string;
    datetime: string;
    home_team: string;
    away_team: string;
    home_goal: string;
    away_goal: string;
    season: string;
  }>(content, { header: true, skipEmptyLines: true });
  
  return result.data
    .filter(row => row.datetime && row.home_team && row.away_team)
    .map(row => {
      const date = parseSoccerDate(row.datetime);
      const homeGoals = Number(row.home_goal) || 0;
      const awayGoals = Number(row.away_goal) || 0;
      
      return {
        date,
        homeTeam: normalizeTeamName(row.home_team),
        awayTeam: normalizeTeamName(row.away_team),
        homeGoals,
        awayGoals,
        season: extractSeason(date, row.season),
        round: row.round,
        competition: 'Copa do Brasil',
        source: 'copa-do-brasil',
        originalData: { ...row }
      };
    });
}

/**
 * Loads and parses Copa Libertadores matches
 */
export function loadLibertadoresMatches(filePath: string): Match[] {
  const content = readFileSync(filePath, 'utf-8');
  const result = parse<{
    datetime: string;
    home_team: string;
    away_team: string;
    home_goal: string;
    away_goal: string;
    season: string;
    stage: string;
  }>(content, { header: true, skipEmptyLines: true });
  
  return result.data
    .filter(row => row.datetime && row.home_team && row.away_team)
    .map(row => {
      const date = parseSoccerDate(row.datetime);
      const homeGoals = Number(row.home_goal) || 0;
      const awayGoals = Number(row.away_goal) || 0;
      
      return {
        date,
        homeTeam: normalizeTeamName(row.home_team),
        awayTeam: normalizeTeamName(row.away_team),
        homeGoals,
        awayGoals,
        season: extractSeason(date, row.season),
        stage: row.stage,
        competition: 'Copa Libertadores',
        source: 'libertadores',
        originalData: { ...row }
      };
    });
}

/**
 * Loads and parses extended match statistics
 */
export function loadExtendedStatsMatches(filePath: string): Match[] {
  const content = readFileSync(filePath, 'utf-8');
  const result = parse<{
    tournament: string;
    home: string;
    away: string;
    home_goal: string;
    away_goal: string;
    home_corner: string;
    away_corner: string;
    home_attack: string;
    away_attack: string;
    home_shots: string;
    away_shots: string;
    time: string;
    date: string;
    ht_result: string;
    at_result: string;
    total_corners: string;
  }>(content, { header: true, skipEmptyLines: true });
  
  return result.data
    .filter(row => row.date && row.home && row.away)
    .map(row => {
      // Combine date and time if available
      const dateTimeStr = row.time ? `${row.date} ${row.time}` : row.date;
      const date = parseSoccerDate(dateTimeStr);
      const homeGoals = Number(row.home_goal) || 0;
      const awayGoals = Number(row.away_goal) || 0;
      
      return {
        date,
        homeTeam: normalizeTeamName(row.home),
        awayTeam: normalizeTeamName(row.away),
        homeGoals,
        awayGoals,
        season: extractSeason(date),
        competition: row.tournament,
        homeCorners: Number(row.home_corner) || undefined,
        awayCorners: Number(row.away_corner) || undefined,
        homeAttacks: Number(row.home_attack) || undefined,
        awayAttacks: Number(row.away_attack) || undefined,
        homeShots: Number(row.home_shots) || undefined,
        awayShots: Number(row.away_shots) || undefined,
        totalCorners: Number(row.total_corners) || undefined,
        source: 'extended-stats',
        originalData: { ...row }
      };
    });
}

/**
 * Loads and parses historical Brasileirão matches (2003-2019)
 */
export function loadHistoricalMatches(filePath: string): Match[] {
  const content = readFileSync(filePath, 'utf-8');
  const result = parse<{
    Data: string;
    Ano: string;
    Rodada: string;
    Equipe_mandante: string;
    Equipe_visitante: string;
    Gols_mandante: string;
    Gols_visitante: string;
    Mandante_UF: string;
    Visitante_UF: string;
    Vencedor: string;
    Arena: string;
  }>(content, { header: true, skipEmptyLines: true });
  
  return result.data
    .filter(row => row.Data && row.Equipe_mandante && row.Equipe_visitante)
    .map(row => {
      const date = parseSoccerDate(row.Data);
      const homeGoals = Number(row.Gols_mandante) || 0;
      const awayGoals = Number(row.Gols_visitante) || 0;
      
      let winner: 'home' | 'away' | 'draw' | undefined;
      if (row.Vencedor === 'Mandante') winner = 'home';
      else if (row.Vencedor === 'Visitante') winner = 'away';
      else if (row.Vencedor === 'Empate') winner = 'draw';
      
      return {
        date,
        homeTeam: normalizeTeamName(row.Equipe_mandante),
        awayTeam: normalizeTeamName(row.Equipe_visitante),
        homeGoals,
        awayGoals,
        season: extractSeason(date, row.Ano),
        round: row.Rodada,
        stadium: row.Arena,
        winner,
        competition: 'Brasileirão Serie A',
        source: 'historical',
        originalData: { ...row }
      };
    });
}

/**
 * Loads and parses FIFA player data
 */
export function loadFifaPlayers(filePath: string): Player[] {
  const content = readFileSync(filePath, 'utf-8');
  const result = parse<{
    ID: string;
    Name: string;
    Age: string;
    Nationality: string;
    Overall: string;
    Potential: string;
    Club: string;
    Position: string;
    'Jersey Number': string;
    Height: string;
    Weight: string;
    'Preferred Foot': string;
    Value: string;
    Wage: string;
    Crossing: string;
    Finishing: string;
    HeadingAccuracy: string;
    ShortPassing: string;
    Dribbling: string;
    ShotPower: string;
    Stamina: string;
    Strength: string;
    Aggression: string;
    Composure: string;
  }>(content, { header: true, skipEmptyLines: true });
  
  const players: Player[] = [];
  
  for (const row of result.data) {
    if (!row.ID || !row.Name || !row.Nationality) continue;
    
    const id = Number(row.ID);
    if (isNaN(id)) continue;
    
    players.push({
      id,
      name: row.Name,
      age: Number(row.Age) || 0,
      nationality: row.Nationality,
      overall: Number(row.Overall) || 0,
      potential: Number(row.Potential) || 0,
      club: row.Club,
      position: row.Position,
      jerseyNumber: Number(row['Jersey Number']) || undefined,
      height: row.Height,
      weight: row.Weight,
      preferredFoot: row['Preferred Foot'],
      value: row.Value,
      wage: row.Wage,
      crossing: Number(row.Crossing) || undefined,
      finishing: Number(row.Finishing) || undefined,
      headingAccuracy: Number(row.HeadingAccuracy) || undefined,
      shortPassing: Number(row.ShortPassing) || undefined,
      dribbling: Number(row.Dribbling) || undefined,
      shotPower: Number(row.ShotPower) || undefined,
      stamina: Number(row.Stamina) || undefined,
      strength: Number(row.Strength) || undefined,
      aggression: Number(row.Aggression) || undefined,
      composure: Number(row.Composure) || undefined,
      source: 'fifa',
      originalData: { ...row }
    });
  }
  
  return players;
}

/**
 * Loads all datasets from their respective files
 */
export function loadAllDatasets(dataDir: string = 'data/kaggle'): {
  matches: Match[];
  players: Player[];
} {
  const matches: Match[] = [
    ...loadBrasileiraoMatches(`${dataDir}/Brasileirao_Matches.csv`),
    ...loadCopaDoBrasilMatches(`${dataDir}/Brazilian_Cup_Matches.csv`),
    ...loadLibertadoresMatches(`${dataDir}/Libertadores_Matches.csv`),
    ...loadExtendedStatsMatches(`${dataDir}/BR-Football-Dataset.csv`),
    ...loadHistoricalMatches(`${dataDir}/novo_campeonato_brasileiro.csv`)
  ];
  
  const players = loadFifaPlayers(`${dataDir}/fifa_data.csv`);
  
  return { matches, players };
}