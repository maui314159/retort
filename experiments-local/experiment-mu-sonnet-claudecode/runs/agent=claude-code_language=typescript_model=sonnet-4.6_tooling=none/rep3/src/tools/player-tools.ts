import { getDataStore } from "../data-loader.js";
import type { Player } from "../types.js";

function playerMatches(player: Player, query: string): boolean {
  return player.name.toLowerCase().includes(query.toLowerCase());
}

function formatPlayer(p: Player, index?: number): string {
  const prefix = index !== undefined ? `${index + 1}. ` : "";
  return `${prefix}${p.name} | Overall: ${p.overall} | Position: ${p.position} | Club: ${p.club} | Nationality: ${p.nationality} | Age: ${p.age}`;
}

export function searchPlayers(params: {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxAge?: number;
  limit?: number;
}): string {
  const { players } = getDataStore();
  const limit = params.limit ?? 20;

  let filtered = players.filter((p) => {
    if (params.name && !playerMatches(p, params.name)) return false;
    if (params.nationality && !p.nationality.toLowerCase().includes(params.nationality.toLowerCase())) return false;
    if (params.club && !p.club.toLowerCase().includes(params.club.toLowerCase())) return false;
    if (params.position && !p.position.toLowerCase().includes(params.position.toLowerCase())) return false;
    if (params.minOverall !== undefined && p.overall < params.minOverall) return false;
    if (params.maxAge !== undefined && p.age > params.maxAge) return false;
    return true;
  });

  filtered.sort((a, b) => b.overall - a.overall);

  const total = filtered.length;
  const shown = filtered.slice(0, limit);

  if (shown.length === 0) return "No players found for the given criteria.";

  const lines = shown.map((p, i) => formatPlayer(p, i));
  const suffix = total > limit ? `\n\n(Showing ${limit} of ${total} players)` : `\n\nTotal: ${total} players`;

  return lines.join("\n") + suffix;
}

export function getPlayerDetails(params: { name: string }): string {
  const { players } = getDataStore();

  const matches = players.filter((p) => playerMatches(p, params.name));
  if (matches.length === 0) return `No player found with name "${params.name}".`;

  const p = matches.sort((a, b) => b.overall - a.overall)[0];

  const lines = [
    `Player: ${p.name}`,
    `Nationality: ${p.nationality}`,
    `Age: ${p.age}`,
    `Club: ${p.club}`,
    `Position: ${p.position}`,
    `Overall Rating: ${p.overall}`,
    `Potential: ${p.potential}`,
    `Value: ${p.value ?? "N/A"}`,
    `Wage: ${p.wage ?? "N/A"}`,
    `Preferred Foot: ${p.preferredFoot ?? "N/A"}`,
    `International Reputation: ${p.internationalReputation ?? "N/A"}/5`,
    `Skill Moves: ${p.skillMoves ?? "N/A"}/5`,
    `Work Rate: ${p.workRate ?? "N/A"}`,
    `Height: ${p.height ?? "N/A"}`,
    `Weight: ${p.weight ?? "N/A"}`,
  ];

  if (p.crossing !== undefined) {
    lines.push(
      "",
      "Key Attributes:",
      `  Crossing: ${p.crossing}`,
      `  Finishing: ${p.finishing ?? "N/A"}`,
      `  Dribbling: ${p.dribbling ?? "N/A"}`,
      `  Short Passing: ${p.passing ?? "N/A"}`,
      `  Shot Power: ${p.shooting ?? "N/A"}`,
      `  Standing Tackle: ${p.defending ?? "N/A"}`,
      `  Strength: ${p.physical ?? "N/A"}`,
      `  Acceleration: ${p.pace ?? "N/A"}`,
    );
  }

  if (matches.length > 1) {
    lines.push("", `Note: ${matches.length - 1} other player(s) also match this name.`);
  }

  return lines.join("\n");
}

export function getBrazilianPlayersAtBrazilianClubs(params: { limit?: number }): string {
  const { players } = getDataStore();

  const BRAZILIAN_CLUBS = [
    "flamengo", "palmeiras", "corinthians", "são paulo", "santos", "grêmio",
    "internacional", "fluminense", "atlético mineiro", "cruzeiro", "vasco",
    "sport", "botafogo", "fortaleza", "ceará", "athletico paranaense",
    "chapecoense", "bahia", "goiás", "coritiba", "bragantino",
  ];

  const limit = params.limit ?? 50;

  const brazilianPlayers = players.filter((p) => {
    if (p.nationality.toLowerCase() !== "brazil") return false;
    const clubLower = p.club.toLowerCase();
    return BRAZILIAN_CLUBS.some((bc) => clubLower.includes(bc));
  });

  brazilianPlayers.sort((a, b) => b.overall - a.overall);

  // Group by club
  const byClub = new Map<string, Player[]>();
  for (const p of brazilianPlayers) {
    const key = p.club;
    if (!byClub.has(key)) byClub.set(key, []);
    byClub.get(key)!.push(p);
  }

  const clubLines: string[] = [];
  const sortedClubs = Array.from(byClub.entries()).sort((a, b) => b[1].length - a[1].length);

  for (const [club, clubPlayers] of sortedClubs) {
    const avg = (clubPlayers.reduce((s, p) => s + p.overall, 0) / clubPlayers.length).toFixed(1);
    clubLines.push(`${club}: ${clubPlayers.length} players (avg rating: ${avg})`);
    const topThree = clubPlayers.slice(0, 3).map((p) => `  - ${p.name} (${p.overall}, ${p.position})`);
    clubLines.push(...topThree);
  }

  const total = brazilianPlayers.length;
  const topOverall = brazilianPlayers.slice(0, 10).map((p, i) => formatPlayer(p, i));

  return [
    `Brazilian players at Brazilian clubs: ${total} total`,
    "",
    "Top-rated Brazilian players at Brazilian clubs:",
    ...topOverall,
    "",
    "By club:",
    ...clubLines.slice(0, limit),
  ].join("\n");
}

export function getTopPlayers(params: {
  nationality?: string;
  position?: string;
  club?: string;
  limit?: number;
}): string {
  const { players } = getDataStore();
  const limit = params.limit ?? 20;

  let filtered = players.filter((p) => {
    if (params.nationality && !p.nationality.toLowerCase().includes(params.nationality.toLowerCase())) return false;
    if (params.position && !p.position.toLowerCase().includes(params.position.toLowerCase())) return false;
    if (params.club && !p.club.toLowerCase().includes(params.club.toLowerCase())) return false;
    return true;
  });

  filtered.sort((a, b) => b.overall - a.overall);
  const shown = filtered.slice(0, limit);

  if (shown.length === 0) return "No players found.";

  const context = [
    params.nationality ? `Nationality: ${params.nationality}` : null,
    params.position ? `Position: ${params.position}` : null,
    params.club ? `Club: ${params.club}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  const lines = shown.map((p, i) => formatPlayer(p, i));
  return [`Top Players${context ? ` (${context})` : ""}`, ...lines].join("\n");
}
