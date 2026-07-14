/**
 * Team statistics tools: win/loss/draw records, goals, performance by competition.
 */

import { teamMatchesSearch, normalizeTeamName } from '../data/normalize.js';
import type { Match, TeamRecord } from '../data/types.js';

function competitionLabel(comp: string): string {
  switch (comp) {
    case 'brasileirao': return 'Brasileirao Serie A';
    case 'copa_do_brasil': return 'Copa do Brasil';
    case 'libertadores': return 'Copa Libertadores';
    case 'historico': return 'Brasileirao (historical)';
    default: return comp.replace(/_/g, ' ');
  }
}

export function getTeamRecord(
  matches: Match[],
  team: string,
  competition?: string,
  season?: number,
  homeOnly?: boolean,
  awayOnly?: boolean
): TeamRecord {
  let filtered = matches.filter(
    (m) => teamMatchesSearch(m.homeTeam, team) || teamMatchesSearch(m.awayTeam, team)
  );

  if (competition) {
    const f = competition.toLowerCase();
    filtered = filtered.filter((m) => {
      const c = m.competition.toLowerCase();
      if (f === 'brasileirao' || f === 'serie a') return c === 'brasileirao' || c === 'historico';
      return c.includes(f) || f.includes(c);
    });
  }

  if (season) filtered = filtered.filter((m) => m.season === season);

  if (homeOnly) filtered = filtered.filter((m) => teamMatchesSearch(m.homeTeam, team));
  if (awayOnly) filtered = filtered.filter((m) => teamMatchesSearch(m.awayTeam, team));

  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

  for (const m of filtered) {
    const isHome = teamMatchesSearch(m.homeTeam, team);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += gf;
    goalsAgainst += ga;
    if (gf > ga) wins++;
    else if (gf === ga) draws++;
    else losses++;
  }

  return {
    team: normalizeTeamName(team),
    played: filtered.length,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    points: wins * 3 + draws,
  };
}

export function formatTeamStats(record: TeamRecord, competition?: string, season?: number): string {
  if (record.played === 0) {
    return `No matches found for ${record.team}${season ? ` in ${season}` : ''}${competition ? ` (${competition})` : ''}.`;
  }

  const winRate = ((record.wins / record.played) * 100).toFixed(1);
  const gd = record.goalsFor - record.goalsAgainst;
  const lines: string[] = [];

  const ctx = [
    competition ? competitionLabel(competition) : 'all competitions',
    season ? String(season) : '',
  ].filter(Boolean).join(' ');

  lines.push(`${record.team}${ctx ? ` — ${ctx}` : ''}:`);
  lines.push(`  Played: ${record.played}`);
  lines.push(`  Wins: ${record.wins}  Draws: ${record.draws}  Losses: ${record.losses}`);
  lines.push(`  Goals For: ${record.goalsFor}  Goals Against: ${record.goalsAgainst}  GD: ${gd >= 0 ? '+' : ''}${gd}`);
  lines.push(`  Points: ${record.points}  Win Rate: ${winRate}%`);

  return lines.join('\n');
}

export function getTopGoalTeams(
  matches: Match[],
  competition?: string,
  season?: number,
  limit = 10
): Array<{ team: string; goals: number; matches: number }> {
  let filtered = matches;
  if (competition) {
    const f = competition.toLowerCase();
    filtered = filtered.filter((m) => {
      const c = m.competition.toLowerCase();
      if (f === 'brasileirao' || f === 'serie a') return c === 'brasileirao' || c === 'historico';
      return c.includes(f) || f.includes(c);
    });
  }
  if (season) filtered = filtered.filter((m) => m.season === season);

  const teamGoals = new Map<string, { goals: number; matches: number }>();

  for (const m of filtered) {
    const home = normalizeTeamName(m.homeTeam);
    const away = normalizeTeamName(m.awayTeam);

    const hEntry = teamGoals.get(home) ?? { goals: 0, matches: 0 };
    hEntry.goals += m.homeGoals;
    hEntry.matches += 1;
    teamGoals.set(home, hEntry);

    const aEntry = teamGoals.get(away) ?? { goals: 0, matches: 0 };
    aEntry.goals += m.awayGoals;
    aEntry.matches += 1;
    teamGoals.set(away, aEntry);
  }

  return Array.from(teamGoals.entries())
    .map(([team, data]) => ({ team, ...data }))
    .sort((a, b) => b.goals - a.goals)
    .slice(0, limit);
}
