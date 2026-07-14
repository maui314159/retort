/**
 * Player query tools: search by name, nationality, club, position, rating.
 */

import type { Player } from '../data/types.js';

export interface PlayerSearchParams {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
}

function strIncludes(haystack: string, needle: string): boolean {
  return haystack.toLowerCase().includes(needle.toLowerCase());
}

export function searchPlayers(players: Player[], params: PlayerSearchParams): Player[] {
  let results = players;

  if (params.name) results = results.filter((p) => strIncludes(p.name, params.name!));
  if (params.nationality) results = results.filter((p) => strIncludes(p.nationality, params.nationality!));
  if (params.club) results = results.filter((p) => strIncludes(p.club, params.club!));
  if (params.position) results = results.filter((p) => strIncludes(p.position, params.position!));
  if (params.minOverall !== undefined) results = results.filter((p) => p.overall >= params.minOverall!);
  if (params.maxOverall !== undefined) results = results.filter((p) => p.overall <= params.maxOverall!);

  results.sort((a, b) => b.overall - a.overall);

  return results.slice(0, params.limit ?? 20);
}

export function formatPlayer(p: Player, rank?: number): string {
  const prefix = rank !== undefined ? `${rank}. ` : '- ';
  const attrs: string[] = [
    `Overall: ${p.overall}`,
    `Potential: ${p.potential}`,
    `Position: ${p.position || 'N/A'}`,
    `Club: ${p.club || 'N/A'}`,
    `Nationality: ${p.nationality}`,
    `Age: ${p.age}`,
  ];
  if (p.height) attrs.push(`Height: ${p.height}`);
  if (p.value) attrs.push(`Value: ${p.value}`);
  return `${prefix}${p.name} — ${attrs.join(', ')}`;
}

export function formatPlayerResults(players: Player[], total: number, params: PlayerSearchParams): string {
  if (players.length === 0) return 'No players found for the given criteria.';

  const lines: string[] = [];
  const ctx: string[] = [];
  if (params.nationality) ctx.push(params.nationality);
  if (params.club) ctx.push(`at ${params.club}`);
  if (params.position) ctx.push(params.position);
  if (params.minOverall) ctx.push(`min rating ${params.minOverall}`);

  lines.push(`Players${ctx.length ? ` (${ctx.join(', ')})` : ''}:`);
  lines.push('');

  for (let i = 0; i < players.length; i++) {
    lines.push(formatPlayer(players[i], i + 1));
  }

  if (total > players.length) {
    lines.push('');
    lines.push(`Showing ${players.length} of ${total} results. Use filters to narrow down.`);
  }

  return lines.join('\n');
}

export function getPlayersByClub(players: Player[], clubs: string[]): Map<string, Player[]> {
  const result = new Map<string, Player[]>();
  for (const club of clubs) {
    const matching = players
      .filter((p) => strIncludes(p.club, club))
      .sort((a, b) => b.overall - a.overall);
    if (matching.length > 0) result.set(club, matching);
  }
  return result;
}
