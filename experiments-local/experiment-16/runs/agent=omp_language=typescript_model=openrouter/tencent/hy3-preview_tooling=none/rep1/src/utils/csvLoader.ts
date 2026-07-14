import { createReadStream } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import csv from 'csv-parser';
import {
  Match,
  Player,
} from '../types/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Load Brasileirao matches from CSV
 */
export async function loadBrasileiraoMatches(): Promise<Match[]> {
  const filePath = join(__dirname, '../../data/kaggle/Brasileirao_Matches.csv');
  const matches: Match[] = [];

  return new Promise((resolve, reject) => {
    createReadStream(filePath)
      .pipe(csv())
      .on('data', (row: any) => {
        matches.push({
          datetime: row.datetime || '',
          homeTeam: normalizeTeamName(row.home_team || ''),
          awayTeam: normalizeTeamName(row.away_team || ''),
          homeGoal: parseInt(row.home_goal) || 0,
          awayGoal: parseInt(row.away_goal) || 0,
          season: parseInt(row.season) || 0,
          competition: 'Brasileirão Serie A',
          round: row.round || '',
          homeTeamState: row.home_team_state || '',
          awayTeamState: row.away_team_state || '',
        });
      })
      .on('end', () => resolve(matches))
      .on('error', reject);
  });
}

/**
 * Load Brazilian Cup matches from CSV
 */
export async function loadBrazilianCupMatches(): Promise<Match[]> {
  const filePath = join(__dirname, '../../data/kaggle/Brazilian_Cup_Matches.csv');
  const matches: Match[] = [];

  return new Promise((resolve, reject) => {
    createReadStream(filePath)
      .pipe(csv())
      .on('data', (row: any) => {
        matches.push({
          datetime: row.datetime || '',
          homeTeam: normalizeTeamName(row.home_team || ''),
          awayTeam: normalizeTeamName(row.away_team || ''),
          homeGoal: parseInt(row.home_goal) || 0,
          awayGoal: parseInt(row.away_goal) || 0,
          season: parseInt(row.season) || 0,
          competition: 'Copa do Brasil',
          round: row.round || '',
        });
      })
      .on('end', () => resolve(matches))
      .on('error', reject);
  });
}

/**
 * Load Libertadores matches from CSV
 */
export async function loadLibertadoresMatches(): Promise<Match[]> {
  const filePath = join(__dirname, '../../data/kaggle/Libertadores_Matches.csv');
  const matches: Match[] = [];

  return new Promise((resolve, reject) => {
    createReadStream(filePath)
      .pipe(csv())
      .on('data', (row: any) => {
        matches.push({
          datetime: row.datetime || '',
          homeTeam: normalizeTeamName(row.home_team || ''),
          awayTeam: normalizeTeamName(row.away_team || ''),
          homeGoal: parseInt(row.home_goal) || 0,
          awayGoal: parseInt(row.away_goal) || 0,
          season: parseInt(row.season) || 0,
          competition: 'Copa Libertadores',
          stage: row.stage || '',
        });
      })
      .on('end', () => resolve(matches))
      .on('error', reject);
  });
}

/**
 * Load BR Football Dataset from CSV
 */
export async function loadBRFootballDataset(): Promise<Match[]> {
  const filePath = join(__dirname, '../../data/kaggle/BR-Football-Dataset.csv');
  const matches: Match[] = [];

  return new Promise((resolve, reject) => {
    createReadStream(filePath)
      .pipe(csv())
      .on('data', (row: any) => {
        matches.push({
          datetime: `${row.date || ''} ${row.time || ''}`.trim(),
          homeTeam: normalizeTeamName(row.home || ''),
          awayTeam: normalizeTeamName(row.away || ''),
          homeGoal: parseFloat(row.home_goal) || 0,
          awayGoal: parseFloat(row.away_goal) || 0,
          season: parseInt((row.date || '').split('-')[0]) || 0,
          competition: row.tournament || 'Unknown',
          homeCorner: parseFloat(row.home_corner) || undefined,
          awayCorner: parseFloat(row.away_corner) || undefined,
          homeAttack: parseFloat(row.home_attack) || undefined,
          awayAttack: parseFloat(row.away_attack) || undefined,
          homeShots: parseFloat(row.home_shots) || undefined,
          awayShots: parseFloat(row.away_shots) || undefined,
        });
      })
      .on('end', () => resolve(matches))
      .on('error', reject);
  });
}

/**
 * Load historical Brasileirao data from CSV
 */
export async function loadHistoricalBrasileirao(): Promise<Match[]> {
  const filePath = join(__dirname, '../../data/kaggle/novo_campeonato_brasileiro.csv');
  const matches: Match[] = [];

  return new Promise((resolve, reject) => {
    createReadStream(filePath)
      .pipe(csv())
      .on('data', (row: any) => {
        // Convert Brazilian date format (DD/MM/YYYY) to ISO
        const dateParts = (row.Data || '').split('/');
        let isoDate = row.Data || '';
        if (dateParts.length === 3) {
          isoDate = `${dateParts[2]}-${dateParts[1].padStart(2, '0')}-${dateParts[0].padStart(2, '0')}`;
        }

        matches.push({
          datetime: isoDate,
          homeTeam: normalizeTeamName(row.Equipe_mandante || ''),
          awayTeam: normalizeTeamName(row.Equipe_visitante || ''),
          homeGoal: parseInt(row.Gols_mandante) || 0,
          awayGoal: parseInt(row.Gols_visitante) || 0,
          season: parseInt(row.Ano) || 0,
          competition: 'Brasileirão Serie A',
          round: row.Rodada || '',
          homeTeamState: row.Mandante_UF || '',
          awayTeamState: row.Visitante_UF || '',
          venue: row.Arena || '',
        });
      })
      .on('end', () => resolve(matches))
      .on('error', reject);
  });
}

/**
 * Load FIFA player data from CSV
 */
export async function loadFIFAData(): Promise<Player[]> {
  const filePath = join(__dirname, '../../data/kaggle/fifa_data.csv');
  const players: Player[] = [];

  return new Promise((resolve, reject) => {
    createReadStream(filePath)
      .pipe(csv())
      .on('data', (row: any) => {
        players.push({
          id: row.ID || '',
          name: row.Name || '',
          age: parseInt(row.Age) || 0,
          nationality: row.Nationality || '',
          overall: parseInt(row.Overall) || 0,
          potential: parseInt(row.Potential) || 0,
          club: row.Club || '',
          position: row.Position || '',
          jerseyNumber: parseInt(row['Jersey Number']) || undefined,
          height: row.Height || '',
          weight: row.Weight || '',
        });
      })
      .on('end', () => resolve(players))
      .on('error', reject);
  });
}

/**
 * Normalize team names for consistent matching
 */
export function normalizeTeamName(name: string): string {
  if (!name) return '';

  // Remove state suffixes like "-SP", "-RJ", etc.
  let normalized = name
    .replace(/-\s*[A-Z]{2}\b/g, '')  // Remove -SP, -RJ, etc.
    .replace(/\s*\([^)]*\)/g, '')     // Remove parentheses content
    .trim();

  // Common name mappings
  const nameMap: Record<string, string> = {
    'São Paulo': 'Sao Paulo',
    'Santos': 'Santos',
    'Palmeiras': 'Palmeiras',
    'Corinthians': 'Corinthians',
    'Flamengo': 'Flamengo',
    'Fluminense': 'Fluminense',
    'Vasco': 'Vasco',
    'Botafogo': 'Botafogo',
    'Grêmio': 'Gremio',
    'Gremio': 'Gremio',
    'Internacional': 'Internacional',
    'Athletico-PR': 'Atletico-PR',
    'Atlético-PR': 'Atletico-PR',
    'Atletico-PR': 'Atletico-PR',
    'Atlético-MG': 'Atletico-MG',
    'Atletico-MG': 'Atletico-MG',
    'Cruzeiro': 'Cruzeiro',
    'Bahia': 'Bahia',
    'Sport': 'Sport',
    'Vitória': 'Vitoria',
    'Vitoria': 'Vitoria',
    'Coritiba': 'Coritiba',
    'Paraná': 'Parana',
    'Parana': 'Parana',
    'Figueirense': 'Figueirense',
    'Ponte Preta': 'Ponte Preta',
    'Náutico': 'Nautico',
    'Nautico': 'Nautico',
    'Ceará': 'Ceara',
    'Ceara': 'Ceara',
    'Fortaleza': 'Fortaleza',
    'Goiás': 'Goias',
    'Goias': 'Goias',
    'Avaí': 'Avai',
    'Avai': 'Avai',
    'Chapecoense': 'Chapecoense',
    'Criciúma': 'Criciuma',
    'Criciuma': 'Criciuma',
    'Juventude': 'Juventude',
    'Bragantino': 'Bragantino',
    'Red Bull Bragantino': 'Bragantino',
    'América-MG': 'America-MG',
    'America-MG': 'America-MG',
    'América-RN': 'America-RN',
    'America-RN': 'America-RN',
  };

  // Check if we have a mapping
  for (const [key, value] of Object.entries(nameMap)) {
    if (normalized.toLowerCase().includes(key.toLowerCase())) {
      return value;
    }
  }

  return normalized;
}

/**
 * Load all match data from all sources
 */
export async function loadAllMatches(): Promise<Match[]> {
  const [
    brasileirao,
    copaDoBrasil,
    libertadores,
    brDataset,
    historical,
  ] = await Promise.all([
    loadBrasileiraoMatches(),
    loadBrazilianCupMatches(),
    loadLibertadoresMatches(),
    loadBRFootballDataset(),
    loadHistoricalBrasileirao(),
  ]);

  return [
    ...brasileirao,
    ...copaDoBrasil,
    ...libertadores,
    ...brDataset,
    ...historical,
  ];
}
