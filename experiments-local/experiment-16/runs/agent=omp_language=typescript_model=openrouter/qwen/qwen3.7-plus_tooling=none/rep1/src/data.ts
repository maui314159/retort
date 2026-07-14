import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'csv-parse/sync';
import { Match, Player } from './types.js';

const DATA_DIR = path.join(process.cwd(), 'data', 'kaggle');

export function normalizeTeamName(name: string): string {
  if (!name) return "";
  let n = name.toLowerCase().trim();
  
  n = n.replace(/\s*-\s*[a-z]{2}\s*$/, "");
  n = n.replace(/\s*\(.*?\)\s*/g, " ").trim();
  n = n.replace(/\s+(fc|futebol clube|esporte clube|sport club|clube de regatas|associação|de desportos)\b/g, "").trim();
  
  const aliases: Record<string, string> = {
    "sport club corinthians paulista": "corinthians",
    "corinthians": "corinthians",
    "são paulo": "são paulo",
    "são paulo fc": "são paulo",
    "cr flamengo": "flamengo",
    "flamengo": "flamengo",
    "se palmeiras": "palmeiras",
    "palmeiras": "palmeiras",
    "santos": "santos",
    "santos fc": "santos",
    "grêmio": "grêmio",
    "grêmio foot-ball porto alegrense": "grêmio",
    "internacional": "internacional",
    "sport club internacional": "internacional",
    "cruzeiro": "cruzeiro",
    "cruzeiro esporte clube": "cruzeiro",
    "fluminense": "fluminense",
    "fluminense fc": "fluminense",
    "botafogo": "botafogo",
    "botafogo de futebol e regatas": "botafogo",
    "vasco da gama": "vasco da gama",
    "club de regatas vasco da gama": "vasco da gama",
    "athletico paranaense": "athletico paranaense",
    "club athletes paranaense": "athletico paranaense",
    "atlético mineiro": "atlético mineiro",
    "clube atlético mineiro": "atlético mineiro",
    "américa mineiro": "américa mineiro",
    "bahia": "bahia",
    "esporte clube bahia": "bahia",
    "fortaleza": "fortaleza",
    "fortaleza esporte clube": "fortaleza",
    "ceará": "ceará",
    "ceará sporting club": "ceará",
    "goiás": "goiás",
    "goiás esporte clube": "goiás",
    "sport recife": "sport recife",
    "sport club do recife": "sport recife",
    "vitória": "vitória",
    "esporte clube vitória": "vitória",
    "coritiba": "coritiba",
    "coritiba foot ball club": "coritiba",
    "chapecoense": "chapecoense",
    "associação chapecoense de futebol": "chapecoense",
    "avaí": "avaí",
    "avaí futebol clube": "avaí",
    "bragantino": "bragantino",
    "red bull bragantino": "bragantino",
    "clube atlético bragantino": "bragantino",
    "juventude": "juventude",
    "cuiabá": "cuiabá",
    "cuiabá esporte clube": "cuiabá",
    "nacional": "nacional",
    "nacional (uru)": "nacional",
    "barcelona": "barcelona",
    "barcelona-equ": "barcelona",
    "boavista": "boavista",
    "boavista sport club (antigo esporte clube barreira)": "boavista",
    "portuguesa": "portuguesa",
    "portuguesa-sp": "portuguesa",
  };

  return aliases[n] || n;
}

function parseDate(dateStr: string): Date | null {
  if (!dateStr) return null;
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr.trim())) {
    const [d, m, y] = dateStr.trim().split('/');
    return new Date(`${y}-${m}-${d}`);
  }
  const parsed = new Date(dateStr);
  return isNaN(parsed.getTime()) ? null : parsed;
}

export async function loadMatches(): Promise<Match[]> {
  const matches: Match[] = [];
  
  const br1Path = path.join(DATA_DIR, 'Brasileirao_Matches.csv');
  if (fs.existsSync(br1Path)) {
    const br1 = fs.readFileSync(br1Path, 'utf-8');
    const br1Records = parse(br1, { columns: true, skip_empty_lines: true }) as Record<string, any>[];
    for (const r of br1Records) {
      matches.push({
        id: `br1_${Math.random()}`,
        date: parseDate(r.datetime) || new Date(),
        season: parseInt(r.season) || 0,
        competition: 'Brasileirão',
        homeTeam: r.home_team,
        awayTeam: r.away_team,
        homeGoals: parseInt(r.home_goal) || 0,
        awayGoals: parseInt(r.away_goal) || 0,
        round: r.round,
      });
    }
  }

  const cupPath = path.join(DATA_DIR, 'Brazilian_Cup_Matches.csv');
  if (fs.existsSync(cupPath)) {
    const cup = fs.readFileSync(cupPath, 'utf-8');
    const cupRecords = parse(cup, { columns: true, skip_empty_lines: true }) as Record<string, any>[];
    for (const r of cupRecords) {
      matches.push({
        id: `cup_${Math.random()}`,
        date: parseDate(r.datetime) || new Date(),
        season: parseInt(r.season) || 0,
        competition: 'Copa do Brasil',
        homeTeam: r.home_team,
        awayTeam: r.away_team,
        homeGoals: parseInt(r.home_goal) || 0,
        awayGoals: parseInt(r.away_goal) || 0,
        round: r.round,
      });
    }
  }

  const libPath = path.join(DATA_DIR, 'Libertadores_Matches.csv');
  if (fs.existsSync(libPath)) {
    const lib = fs.readFileSync(libPath, 'utf-8');
    const libRecords = parse(lib, { columns: true, skip_empty_lines: true }) as Record<string, any>[];
    for (const r of libRecords) {
      matches.push({
        id: `lib_${Math.random()}`,
        date: parseDate(r.datetime) || new Date(),
        season: parseInt(r.season) || 0,
        competition: 'Copa Libertadores',
        homeTeam: r.home_team,
        awayTeam: r.away_team,
        homeGoals: parseInt(r.home_goal) || 0,
        awayGoals: parseInt(r.away_goal) || 0,
        stage: r.stage,
      });
    }
  }

  const br2Path = path.join(DATA_DIR, 'BR-Football-Dataset.csv');
  if (fs.existsSync(br2Path)) {
    const br2 = fs.readFileSync(br2Path, 'utf-8');
    const br2Records = parse(br2, { columns: true, skip_empty_lines: true }) as Record<string, any>[];
    for (const r of br2Records) {
      matches.push({
        id: `br2_${Math.random()}`,
        date: parseDate(r.date) || new Date(),
        season: parseInt(r.date?.split('-')[0]) || 0,
        competition: r.tournament || 'Unknown',
        homeTeam: r.home,
        awayTeam: r.away,
        homeGoals: parseFloat(r.home_goal) || 0,
        awayGoals: parseFloat(r.away_goal) || 0,
      });
    }
  }

  const br3Path = path.join(DATA_DIR, 'novo_campeonato_brasileiro.csv');
  if (fs.existsSync(br3Path)) {
    const br3 = fs.readFileSync(br3Path, 'utf-8');
    const br3Records = parse(br3, { columns: true, skip_empty_lines: true, encoding: 'utf8' }) as Record<string, any>[];
    for (const r of br3Records) {
      matches.push({
        id: `br3_${r.ID || Math.random()}`,
        date: parseDate(r.Data) || new Date(),
        season: parseInt(r.Ano) || 0,
        competition: 'Brasileirão',
        homeTeam: r.Equipe_mandante,
        awayTeam: r.Equipe_visitante,
        homeGoals: parseInt(r.Gols_mandante) || 0,
        awayGoals: parseInt(r.Gols_visitante) || 0,
        round: r.Rodada,
        arena: r.Arena,
      });
    }
  }

  return matches;
}

export async function loadPlayers(): Promise<Player[]> {
  const fifaPath = path.join(DATA_DIR, 'fifa_data.csv');
  if (!fs.existsSync(fifaPath)) {
    return [];
  }
  const fifa = fs.readFileSync(fifaPath, 'utf-8');
  const records = parse(fifa, { columns: true, skip_empty_lines: true, encoding: 'utf8', relax_quotes: true }) as Record<string, any>[];
  const players: Player[] = [];
  
  for (const r of records) {
    players.push({
      id: r.ID || String(Math.random()),
      name: r.Name || '',
      age: parseInt(r.Age) || 0,
      nationality: r.Nationality || '',
      overall: parseInt(r.Overall) || 0,
      potential: parseInt(r.Potential) || 0,
      club: r.Club || '',
      position: r.Position || '',
      height: r.Height,
      weight: r.Weight,
    });
  }
  
  return players;
}