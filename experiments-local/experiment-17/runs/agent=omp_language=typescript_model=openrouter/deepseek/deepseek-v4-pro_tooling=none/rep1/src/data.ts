/**
 * Brazilian Soccer MCP Server - Data Loading
 *
 * Loads and normalizes all 6 CSV datasets into in-memory structures.
 * Handles multiple date formats, team name variations, and UTF-8 encoding.
 */

import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { NormalizedMatch, NormalizedPlayer } from './types.js';
import { normalizeTeam } from './normalize.js';

// ── Path resolution ──────────────────────────────────────────────────

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, '..', 'data', 'kaggle');

// ── CSV parser ───────────────────────────────────────────────────────

/**
 * Parse a CSV line respecting quoted fields.
 * Handles quoted strings containing commas and newlines.
 */
function parseCSVLine(line: string): string[] {
  const fields: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === ',' && !inQuotes) {
      fields.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  fields.push(current.trim());
  return fields;
}

/**
 * Read a CSV file and return rows as Record<string, string>[].
 * Strips BOM from first field name.
 */
function readCSV(filename: string): Record<string, string>[] {
  const path = resolve(DATA_DIR, filename);
  const text = readFileSync(path, 'utf-8');
  const lines = text.split(/\r?\n/).filter(l => l.trim());

  if (lines.length === 0) return [];

  // Parse header, strip BOM and quotes
  const headers = parseCSVLine(lines[0]).map(h =>
    h.replace(/^\ufeff/, '').replace(/^"|"$/g, '')
  );

  const rows: Record<string, string>[] = [];
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    const row: Record<string, string> = {};
    for (let j = 0; j < headers.length; j++) {
      let val = values[j] ?? '';
      // Unquote
      if (val.startsWith('"') && val.endsWith('"')) {
        val = val.slice(1, -1);
      }
      row[headers[j]] = val;
    }
    rows.push(row);
  }
  return rows;
}

// ── Date parsing ─────────────────────────────────────────────────────

/**
 * Parse various date formats into ISO date string YYYY-MM-DD.
 * Supported formats:
 *   - "2023-09-24"
 *   - "2012-05-19 18:30:00"
 *   - "29/03/2003"
 */
function parseDate(raw: string): string {
  if (!raw || !raw.trim()) return '';

  // Strip time portion: "2012-05-19 18:30:00" -> "2012-05-19"
  const datePart = raw.trim().split(/\s+/)[0];

  // ISO: "YYYY-MM-DD"
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    return datePart;
  }

  // Brazilian: "DD/MM/YYYY"
  const brMatch = datePart.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) {
    return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  }

  // Try native Date as fallback
  const d = new Date(datePart);
  if (!isNaN(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  return '';
}

// ── Data stores ──────────────────────────────────────────────────────

let _matches: NormalizedMatch[] | null = null;
let _players: NormalizedPlayer[] | null = null;
let _loaded = false;

// ── Match loading ────────────────────────────────────────────────────

function loadBrasileirao(): NormalizedMatch[] {
  const rows = readCSV('Brasileirao_Matches.csv');
  return rows.map(r => {
    const home = normalizeTeam(r.home_team);
    const away = normalizeTeam(r.away_team);
    return {
      date: parseDate(r.datetime),
      homeTeam: home.key,
      homeTeamDisplay: home.display,
      awayTeam: away.key,
      awayTeamDisplay: away.display,
      homeGoal: parseInt(r.home_goal, 10) || 0,
      awayGoal: parseInt(r.away_goal, 10) || 0,
      season: parseInt(r.season, 10) || 0,
      competition: 'brasileirao',
      round: r.round || '',
      stage: '',
    };
  });
}

function loadCopaDoBrasil(): NormalizedMatch[] {
  const rows = readCSV('Brazilian_Cup_Matches.csv');
  return rows.map(r => {
    const home = normalizeTeam(r.home_team);
    const away = normalizeTeam(r.away_team);
    return {
      date: parseDate(r.datetime),
      homeTeam: home.key,
      homeTeamDisplay: home.display,
      awayTeam: away.key,
      awayTeamDisplay: away.display,
      homeGoal: parseInt(r.home_goal, 10) || 0,
      awayGoal: parseInt(r.away_goal, 10) || 0,
      season: parseInt(r.season, 10) || 0,
      competition: 'copa_do_brasil',
      round: r.round || '',
      stage: '',
    };
  });
}

function loadLibertadores(): NormalizedMatch[] {
  const rows = readCSV('Libertadores_Matches.csv');
  return rows.map(r => {
    const home = normalizeTeam(r.home_team);
    const away = normalizeTeam(r.away_team);
    return {
      date: parseDate(r.datetime),
      homeTeam: home.key,
      homeTeamDisplay: home.display,
      awayTeam: away.key,
      awayTeamDisplay: away.display,
      homeGoal: parseInt(r.home_goal, 10) || 0,
      awayGoal: parseInt(r.away_goal, 10) || 0,
      season: parseInt(r.season, 10) || 0,
      competition: 'libertadores',
      round: '',
      stage: (r.stage || '').toLowerCase(),
    };
  });
}

function loadBRFootball(): NormalizedMatch[] {
  const rows = readCSV('BR-Football-Dataset.csv');
  return rows.map(r => {
    const home = normalizeTeam(r.home);
    const away = normalizeTeam(r.away);
    const comp = (r.tournament || '').toLowerCase();

    // Map competition names to our standardized ones
    let competition: string;
    if (comp.includes('brasileir') || comp.includes('serie a') || comp.includes('série a')) {
      competition = 'brasileirao';
    } else if (comp.includes('copa do brasil')) {
      competition = 'copa_do_brasil';
    } else if (comp.includes('libertadores')) {
      competition = 'libertadores';
    } else {
      competition = comp.replace(/\s+/g, '_');
    }

    // Parse season from date (YYYY-MM-DD)
    const dateStr = parseDate(r.date || '');
    const season = dateStr ? parseInt(dateStr.slice(0, 4), 10) : 0;

    return {
      date: dateStr,
      homeTeam: home.key,
      homeTeamDisplay: home.display,
      awayTeam: away.key,
      awayTeamDisplay: away.display,
      homeGoal: parseFloat(r.home_goal) || 0,
      awayGoal: parseFloat(r.away_goal) || 0,
      season,
      competition,
      round: '',
      stage: '',
      homeCorner: r.home_corner ? parseFloat(r.home_corner) : undefined,
      awayCorner: r.away_corner ? parseFloat(r.away_corner) : undefined,
      homeShots: r.home_shots ? parseFloat(r.home_shots) : undefined,
      awayShots: r.away_shots ? parseFloat(r.away_shots) : undefined,
      homeAttack: r.home_attack ? parseFloat(r.home_attack) : undefined,
      awayAttack: r.away_attack ? parseFloat(r.away_attack) : undefined,
    };
  });
}

function loadNovoBrasileirao(): NormalizedMatch[] {
  const rows = readCSV('novo_campeonato_brasileiro.csv');
  return rows.map(r => {
    const home = normalizeTeam(r.Equipe_mandante);
    const away = normalizeTeam(r.Equipe_visitante);
    return {
      date: parseDate(r.Data),
      homeTeam: home.key,
      homeTeamDisplay: home.display,
      awayTeam: away.key,
      awayTeamDisplay: away.display,
      homeGoal: parseInt(r.Gols_mandante, 10) || 0,
      awayGoal: parseInt(r.Gols_visitante, 10) || 0,
      season: parseInt(r.Ano, 10) || 0,
      competition: 'brasileirao',
      round: r.Rodada || '',
      stage: '',
      stadium: r.Arena || undefined,
    };
  });
}

// ── Player loading ───────────────────────────────────────────────────

function loadFifaPlayers(): NormalizedPlayer[] {
  const rows = readCSV('fifa_data.csv');
  return rows.map(r => {
    const club = normalizeTeam(r.Club);
    // Calculate composite skill ratings (simple averages of related stats)
    const pace = Math.round(
      ((parseFloat(r.Acceleration) || 0) + (parseFloat(r.SprintSpeed) || 0)) / 2
    );
    const shooting = Math.round(
      ((parseFloat(r.Finishing) || 0) + (parseFloat(r.ShotPower) || 0) +
        (parseFloat(r.LongShots) || 0) + (parseFloat(r.Volleys) || 0) +
        (parseFloat(r.Penalties) || 0)) / 5
    );
    const passing = Math.round(
      ((parseFloat(r.ShortPassing) || 0) + (parseFloat(r.LongPassing) || 0) +
        (parseFloat(r.Vision) || 0) + (parseFloat(r.Crossing) || 0) +
        (parseFloat(r.FKAccuracy) || 0) + (parseFloat(r.Curve) || 0)) / 6
    );
    const dribbling = Math.round(
      ((parseFloat(r.Dribbling) || 0) + (parseFloat(r.BallControl) || 0) +
        (parseFloat(r.Agility) || 0) + (parseFloat(r.Balance) || 0)) / 4
    );
    const defending = Math.round(
      ((parseFloat(r.Marking) || 0) + (parseFloat(r.StandingTackle) || 0) +
        (parseFloat(r.SlidingTackle) || 0) + (parseFloat(r.Interceptions) || 0)) / 4
    );
    const physical = Math.round(
      ((parseFloat(r.Stamina) || 0) + (parseFloat(r.Strength) || 0) +
        (parseFloat(r.Jumping) || 0) + (parseFloat(r.Aggression) || 0)) / 4
    );

    return {
      id: parseInt(r.ID, 10) || 0,
      name: (r.Name || '').trim(),
      age: parseInt(r.Age, 10) || 0,
      nationality: (r.Nationality || '').trim(),
      overall: parseInt(r.Overall, 10) || 0,
      potential: parseInt(r.Potential, 10) || 0,
      club: club.key,
      clubDisplay: club.display || (r.Club || '').trim(),
      position: (r.Position || '').trim(),
      jerseyNumber: parseInt(r['Jersey Number'], 10) || 0,
      height: parseFloat(r.Height?.replace('cm', '').trim()) || 0,
      weight: parseFloat(r.Weight?.replace('kg', '').trim()) || 0,
      preferredFoot: (r['Preferred Foot'] || '').trim(),
      skillMoves: parseInt(r['Skill Moves'], 10) || 0,
      weakFoot: parseInt(r['Weak Foot'], 10) || 0,
      workRate: (r['Work Rate'] || '').trim(),
      pace,
      shooting,
      passing,
      dribbling,
      defending,
      physical,
    };
  });
}

// ── Public API ───────────────────────────────────────────────────────

export function loadAllData(): void {
  if (_loaded) return;

  _matches = [
    ...loadBrasileirao(),
    ...loadCopaDoBrasil(),
    ...loadLibertadores(),
    ...loadBRFootball(),
    ...loadNovoBrasileirao(),
  ];

  _players = loadFifaPlayers();
  _loaded = true;
}

export function getMatches(): NormalizedMatch[] {
  loadAllData();
  return _matches!;
}

export function getPlayers(): NormalizedPlayer[] {
  loadAllData();
  return _players!;
}

export function getMatchCount(): number {
  loadAllData();
  return _matches!.length;
}

export function getPlayerCount(): number {
  loadAllData();
  return _players!.length;
}
