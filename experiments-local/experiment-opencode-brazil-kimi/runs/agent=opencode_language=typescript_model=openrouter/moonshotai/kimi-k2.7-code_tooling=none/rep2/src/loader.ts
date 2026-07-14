import { readFileSync } from 'node:fs';
import { parse } from 'csv-parse/sync';
import type { Match, Player } from './types.js';
import { canonicalTeamKey, normalizeTeamName, normalizeCompetition, parseNumber, parseDate, formatDate } from './normalize.js';

const DATA_DIR = new URL('../data/kaggle', import.meta.url);

export interface LoadedData {
  matches: Match[];
  players: Player[];
}

function loadCsv(path: string): Record<string, unknown>[] {
  const content = readFileSync(path, 'utf-8');
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    cast: false,
  });
}

function parseDatetime(value: string, dateValue?: string, timeValue?: string): { date?: string; time?: string; datetime?: Date } {
  if (value) {
    const dt = parseDate(value);
    if (dt) {
      return {
        datetime: dt,
        date: formatDate(dt),
        time: value.split(' ')[1]?.slice(0, 5),
      };
    }
  }
  if (dateValue) {
    const dt = parseDate(dateValue);
    if (dt) {
      return {
        datetime: dt,
        date: formatDate(dt),
        time: timeValue?.slice(0, 5),
      };
    }
  }
  return {};
}

function inferWinner(home: number, away: number): 'home' | 'away' | 'draw' {
  if (home > away) return 'home';
  if (away > home) return 'away';
  return 'draw';
}

export async function loadData(dataDir?: string): Promise<LoadedData> {
  const base = dataDir
    ? new URL(`file://${dataDir.endsWith('/') ? dataDir : dataDir + '/'}`)
    : DATA_DIR;
  let dirPath = base.pathname;
  if (!dirPath.endsWith('/')) dirPath += '/';

  const matches: Match[] = [];

  // 1. Brasileirão Serie A Matches
  const brasileiraoRows = loadCsv(`${dirPath}Brasileirao_Matches.csv`);
  for (let i = 0; i < brasileiraoRows.length; i++) {
    const row = brasileiraoRows[i];
    const home = normalizeTeamName(String(row.home_team ?? ''));
    const away = normalizeTeamName(String(row.away_team ?? ''));
    const homeGoal = parseNumber(row.home_goal) ?? 0;
    const awayGoal = parseNumber(row.away_goal) ?? 0;
    const dt = parseDatetime(String(row.datetime ?? ''));
    matches.push({
      id: `bra-${i}`,
      ...dt,
      season: parseNumber(row.season) ?? 0,
      competition: 'Brasileirão',
      round: row.round ? String(row.round) : undefined,
      home_team: home,
      home_team_state: row.home_team_state ? String(row.home_team_state) : undefined,
      away_team: away,
      away_team_state: row.away_team_state ? String(row.away_team_state) : undefined,
      home_goal: homeGoal,
      away_goal: awayGoal,
      winner: inferWinner(homeGoal, awayGoal),
      source: 'Brasileirao_Matches.csv',
    });
  }

  // 2. Copa do Brasil
  const copaRows = loadCsv(`${dirPath}Brazilian_Cup_Matches.csv`);
  for (let i = 0; i < copaRows.length; i++) {
    const row = copaRows[i];
    const home = normalizeTeamName(String(row.home_team ?? ''));
    const away = normalizeTeamName(String(row.away_team ?? ''));
    const homeGoal = parseNumber(row.home_goal) ?? 0;
    const awayGoal = parseNumber(row.away_goal) ?? 0;
    const dt = parseDatetime(String(row.datetime ?? ''));
    matches.push({
      id: `copa-${i}`,
      ...dt,
      season: parseNumber(row.season) ?? 0,
      competition: 'Copa do Brasil',
      round: row.round ? String(row.round) : undefined,
      home_team: home,
      away_team: away,
      home_goal: homeGoal,
      away_goal: awayGoal,
      winner: inferWinner(homeGoal, awayGoal),
      source: 'Brazilian_Cup_Matches.csv',
    });
  }

  // 3. Copa Libertadores
  const libRows = loadCsv(`${dirPath}Libertadores_Matches.csv`);
  for (let i = 0; i < libRows.length; i++) {
    const row = libRows[i];
    const home = normalizeTeamName(String(row.home_team ?? ''));
    const away = normalizeTeamName(String(row.away_team ?? ''));
    const homeGoal = parseNumber(row.home_goal) ?? 0;
    const awayGoal = parseNumber(row.away_goal) ?? 0;
    const dt = parseDatetime(String(row.datetime ?? ''));
    matches.push({
      id: `lib-${i}`,
      ...dt,
      season: parseNumber(row.season) ?? 0,
      competition: 'Copa Libertadores',
      stage: row.stage ? String(row.stage) : undefined,
      home_team: home,
      away_team: away,
      home_goal: homeGoal,
      away_goal: awayGoal,
      winner: inferWinner(homeGoal, awayGoal),
      source: 'Libertadores_Matches.csv',
    });
  }

  // 4. Extended Match Statistics
  const extRows = loadCsv(`${dirPath}BR-Football-Dataset.csv`);
  for (let i = 0; i < extRows.length; i++) {
    const row = extRows[i];
    const home = normalizeTeamName(String(row.home ?? ''));
    const away = normalizeTeamName(String(row.away ?? ''));
    if (!home && !away) continue;
    const homeGoal = parseNumber(row.home_goal) ?? 0;
    const awayGoal = parseNumber(row.away_goal) ?? 0;
    const dt = parseDatetime('', String(row.date ?? ''), String(row.time ?? ''));
    matches.push({
      id: `ext-${i}`,
      ...dt,
      season: dt.datetime ? dt.datetime.getFullYear() : 0,
      competition: normalizeCompetition(String(row.tournament ?? '')),
      home_team: home,
      away_team: away,
      home_goal: homeGoal,
      away_goal: awayGoal,
      winner: inferWinner(homeGoal, awayGoal),
      source: 'BR-Football-Dataset.csv',
    });
  }

  // 5. Historical Brasileirão (2003-2019)
  const histRows = loadCsv(`${dirPath}novo_campeonato_brasileiro.csv`);
  for (let i = 0; i < histRows.length; i++) {
    const row = histRows[i];
    const home = normalizeTeamName(String(row.Equipe_mandante ?? ''));
    const away = normalizeTeamName(String(row.Equipe_visitante ?? ''));
    const homeGoal = parseNumber(row.Gols_mandante) ?? 0;
    const awayGoal = parseNumber(row.Gols_visitante) ?? 0;
    const dt = parseDatetime(String(row.Data ?? ''));
    const winnerRaw = String(row.Vencedor ?? '').toLowerCase();
    let winner: 'home' | 'away' | 'draw' = inferWinner(homeGoal, awayGoal);
    if (winnerRaw.includes('mandante')) winner = 'home';
    else if (winnerRaw.includes('visitante')) winner = 'away';
    else if (winnerRaw.includes('empate')) winner = 'draw';
    matches.push({
      id: `hist-${row.ID ?? i}`,
      ...dt,
      season: parseNumber(row.Ano) ?? 0,
      competition: 'Brasileirão',
      round: row.Rodada ? String(row.Rodada) : undefined,
      home_team: home,
      home_team_state: row.Mandante_UF ? String(row.Mandante_UF) : undefined,
      away_team: away,
      away_team_state: row.Visitante_UF ? String(row.Visitante_UF) : undefined,
      home_goal: homeGoal,
      away_goal: awayGoal,
      winner,
      stadium: row.Arena ? String(row.Arena) : undefined,
      source: 'novo_campeonato_brasileiro.csv',
    });
  }

  // 6. FIFA Player Database
  const fifaRows = loadCsv(`${dirPath}fifa_data.csv`);
  const players: Player[] = [];
  for (let i = 0; i < fifaRows.length; i++) {
    const row = fifaRows[i];
    const id = parseNumber(row.ID);
    if (id === undefined) continue;
    const name = String(row.Name ?? '');
    if (!name) continue;
    const club = String(row.Club ?? '');
    const player: Player = {
      id,
      name,
      age: parseNumber(row.Age),
      nationality: row.Nationality ? String(row.Nationality) : undefined,
      overall: parseNumber(row.Overall),
      potential: parseNumber(row.Potential),
      club: club || undefined,
      position: row.Position ? String(row.Position) : undefined,
      jerseyNumber: row['Jersey Number'] ? String(row['Jersey Number']) : undefined,
      height: row.Height ? String(row.Height) : undefined,
      weight: row.Weight ? String(row.Weight) : undefined,
    };
    players.push(player);
  }

  return { matches, players };
}

export { canonicalTeamKey };
