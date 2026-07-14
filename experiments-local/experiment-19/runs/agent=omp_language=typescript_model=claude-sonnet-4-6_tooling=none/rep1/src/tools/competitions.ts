/**
 * Competition tools: standings tables, season overviews.
 *
 * Standings are calculated from match results:
 *   Win = 3 pts, Draw = 1 pt, Loss = 0 pts
 *
 * For Brasileirao, both 'brasileirao' and 'historico' sources are searched
 * based on the requested season.
 */

import { normalizeTeamName, teamMatchesSearch } from '../data/normalize.js';
import type { Match, TeamRecord } from '../data/types.js';

function pickCompetitionForSeason(competition: string, season: number): string[] {
  const c = competition.toLowerCase();
  if (c === 'brasileirao' || c === 'serie a') {
    // historico covers 2003-2019; brasileirao covers 2012+
    // Prefer historico for pre-2020, brasileirao for 2020+
    if (season < 2012) return ['historico'];
    if (season > 2019) return ['brasileirao'];
    // Both datasets cover 2012-2019; use brasileirao as primary (more structured)
    return ['brasileirao', 'historico'];
  }
  if (c === 'copa_do_brasil' || c === 'copa') return ['copa_do_brasil'];
  if (c === 'libertadores') return ['libertadores'];
  return [c];
}

export function getStandings(matches: Match[], competition: string, season: number): TeamRecord[] {
  const sources = pickCompetitionForSeason(competition, season);

  let filtered = matches.filter(
    (m) => m.season === season && sources.some((s) => m.competition.toLowerCase() === s)
  );

  // Deduplicate: if both historico and brasileirao are sources, keep brasileirao rows only
  if (sources.length > 1) {
    const brasileiraoMatches = filtered.filter((m) => m.competition === 'brasileirao');
    if (brasileiraoMatches.length > 0) {
      filtered = brasileiraoMatches;
    }
  }

  const records = new Map<string, TeamRecord>();

  function getOrCreate(teamRaw: string): TeamRecord {
    // Use original (not normalized) team name as key to distinguish
    // teams like "Atletico-MG" vs "Atletico-PR" that share a normalized name.
    const key = teamRaw.trim().toLowerCase();
    if (!records.has(key)) {
      records.set(key, {
        team: normalizeTeamName(teamRaw),
        played: 0, wins: 0, draws: 0, losses: 0,
        goalsFor: 0, goalsAgainst: 0, points: 0,
      });
    }
    return records.get(key)!;
  }

  for (const m of filtered) {
    const home = getOrCreate(m.homeTeam);
    const away = getOrCreate(m.awayTeam);

    home.played++;
    away.played++;
    home.goalsFor += m.homeGoals;
    home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals;
    away.goalsAgainst += m.homeGoals;

    if (m.homeGoals > m.awayGoals) {
      home.wins++;
      home.points += 3;
      away.losses++;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins++;
      away.points += 3;
      home.losses++;
    } else {
      home.draws++;
      home.points++;
      away.draws++;
      away.points++;
    }
  }

  return Array.from(records.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goalsFor - a.goalsAgainst;
    const gdB = b.goalsFor - b.goalsAgainst;
    if (gdB !== gdA) return gdB - gdA;
    return b.goalsFor - a.goalsFor;
  });
}

export function formatStandings(standings: TeamRecord[], competition: string, season: number): string {
  if (standings.length === 0) {
    return `No match data found for ${competition} season ${season}.`;
  }

  const lines: string[] = [];
  lines.push(`${competition.replace(/_/g, ' ')} ${season} Standings (calculated from match results):`);
  lines.push('');
  lines.push('Pos  Team                   Pld  W   D   L   GF  GA  GD   Pts');
  lines.push('─'.repeat(65));

  for (let i = 0; i < standings.length; i++) {
    const r = standings[i];
    const gd = r.goalsFor - r.goalsAgainst;
    const gdStr = `${gd >= 0 ? '+' : ''}${gd}`;
    const pos = String(i + 1).padStart(2);
    const team = r.team.padEnd(22).slice(0, 22);
    const note = i === 0 ? ' ← Champion' : '';
    lines.push(
      `${pos}   ${team} ${String(r.played).padStart(3)}  ${String(r.wins).padStart(2)}  ${String(r.draws).padStart(2)}  ${String(r.losses).padStart(2)}  ${String(r.goalsFor).padStart(3)} ${String(r.goalsAgainst).padStart(3)} ${gdStr.padStart(4)}  ${String(r.points).padStart(3)}${note}`
    );
  }

  return lines.join('\n');
}

export function getAvailableSeasons(matches: Match[], competition?: string): number[] {
  let filtered = matches;
  if (competition) {
    const f = competition.toLowerCase();
    filtered = filtered.filter((m) => m.competition.toLowerCase().includes(f) || f.includes(m.competition.toLowerCase()));
  }
  const seasons = [...new Set(filtered.map((m) => m.season).filter((s) => s > 0))];
  return seasons.sort((a, b) => a - b);
}

export function getSeasonsForTeam(matches: Match[], team: string, competition?: string): number[] {
  let filtered = matches.filter(
    (m) => teamMatchesSearch(m.homeTeam, team) || teamMatchesSearch(m.awayTeam, team)
  );
  if (competition) {
    const f = competition.toLowerCase();
    filtered = filtered.filter((m) => m.competition.toLowerCase().includes(f));
  }
  const seasons = [...new Set(filtered.map((m) => m.season).filter((s) => s > 0))];
  return seasons.sort((a, b) => a - b);
}
