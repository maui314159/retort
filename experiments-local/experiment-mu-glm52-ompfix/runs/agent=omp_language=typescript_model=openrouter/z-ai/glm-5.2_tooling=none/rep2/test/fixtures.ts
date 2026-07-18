/**
 * Brazilian Soccer MCP Server — test dataset factory
 * --------------------------------------------------
 * Context block:
 *   Unit/BDD tests run against small, deterministic, in-memory datasets so the
 *   assertions don't depend on the real multi-megabyte Kaggle files. These
 *   fixtures exercise every normalisation edge case the real data presents:
 *   state suffixes, accented names, NA goals, multiple date formats, and
 *   cross-file team spelling variants.
 */

import type { Match, Player } from "../src/types.js";
import type { Dataset } from "../src/loader.js";

/** Build a test match with sensible defaults; overrides win. */
export function buildMatch(overrides: Partial<Match> & { homeTeam: string; awayTeam: string }): Match {
  return {
    id: overrides.id ?? `test-${overrides.homeTeam}-${overrides.awayTeam}`,
    source: overrides.source ?? "brasileirao",
    competition: overrides.competition ?? "Brasileirão",
    homeTeamDisplay: overrides.homeTeamDisplay ?? overrides.homeTeam,
    awayTeamDisplay: overrides.awayTeamDisplay ?? overrides.awayTeam,
    homeGoal: overrides.homeGoal ?? 1,
    awayGoal: overrides.awayGoal ?? 0,
    season: overrides.season ?? 2023,
    round: overrides.round ?? "1",
    date: overrides.date ?? new Date(Date.UTC(2023, 0, 1)),
    rawDate: overrides.rawDate ?? "2023-01-01",
    ...overrides,
  };
}

/** A compact test dataset covering team-name and date edge cases. */
export function buildDataset(): Dataset {
  const matches: Match[] = [
    // Same team, spelled three ways across sources → same canonical key.
    buildMatch({
      id: "br-1", source: "brasileirao",
      homeTeam: "flamengo", homeTeamDisplay: "Flamengo",
      awayTeam: "fluminense", awayTeamDisplay: "Fluminense",
      homeGoal: 2, awayGoal: 1, season: 2023, round: "22",
      date: new Date(Date.UTC(2023, 8, 3)), rawDate: "2023-09-03 16:00:00",
    }),
    buildMatch({
      id: "br-2", source: "brasileirao",
      homeTeam: "fluminense", homeTeamDisplay: "Fluminense",
      awayTeam: "flamengo", awayTeamDisplay: "Flamengo",
      homeGoal: 1, awayGoal: 0, season: 2023, round: "8",
      date: new Date(Date.UTC(2023, 4, 28)), rawDate: "2023-05-28 16:00:00",
    }),
    buildMatch({
      id: "br-3", source: "brasileirao",
      homeTeam: "palmeiras", homeTeamDisplay: "Palmeiras",
      awayTeam: "sao_paulo", awayTeamDisplay: "São Paulo",
      homeGoal: 3, awayGoal: 0, season: 2023, round: "10",
      date: new Date(Date.UTC(2023, 6, 1)), rawDate: "2023-07-01",
    }),
    buildMatch({
      id: "br-4", source: "brasileirao",
      homeTeam: "corinthians", homeTeamDisplay: "Corinthians",
      awayTeam: "palmeiras", awayTeamDisplay: "Palmeiras",
      homeGoal: 1, awayGoal: 1, season: 2023, round: "11",
      date: new Date(Date.UTC(2023, 6, 8)), rawDate: "2023-07-08",
    }),
    buildMatch({
      id: "br-5", source: "brasileirao",
      homeTeam: "flamengo", homeTeamDisplay: "Flamengo",
      awayTeam: "palmeiras", awayTeamDisplay: "Palmeiras",
      homeGoal: 5, awayGoal: 0, season: 2023, round: "12",
      date: new Date(Date.UTC(2023, 9, 27)), rawDate: "2023-10-27",
    }),
    // Historical dataset: Brazilian date format, accented names.
    buildMatch({
      id: "hist-1", source: "historico",
      homeTeam: "sao_paulo", homeTeamDisplay: "São Paulo",
      awayTeam: "gremio", awayTeamDisplay: "Grêmio",
      homeGoal: 2, awayGoal: 2, season: 2019, round: "20",
      date: new Date(Date.UTC(2019, 8, 15)), rawDate: "15/09/2019",
    }),
    buildMatch({
      id: "hist-2", source: "historico",
      homeTeam: "flamengo", homeTeamDisplay: "Flamengo",
      awayTeam: "santos", awayTeamDisplay: "Santos",
      homeGoal: 4, awayGoal: 1, season: 2019, round: "25",
      date: new Date(Date.UTC(2019, 10, 1)), rawDate: "01/11/2019",
    }),
    // Copa do Brasil with spaced suffix "Flamengo - RJ".
    buildMatch({
      id: "cup-1", source: "copa_do_brasil", competition: "Copa do Brasil",
      homeTeam: "flamengo", homeTeamDisplay: "Flamengo",
      awayTeam: "internacional", awayTeamDisplay: "Internacional",
      homeGoal: 2, awayGoal: 2, season: 2022, round: "4",
      date: new Date(Date.UTC(2022, 6, 14)), rawDate: "2022-07-14 20:00:00",
    }),
    // NA goals (unplayed match).
    buildMatch({
      id: "lib-1", source: "libertadores", competition: "Copa Libertadores",
      homeTeam: "flamengo", homeTeamDisplay: "Flamengo",
      awayTeam: "atletico_mg", awayTeamDisplay: "Atlético Mineiro",
      homeGoal: null, awayGoal: null, season: 2024, round: null, stage: "final",
      date: new Date(Date.UTC(2024, 10, 30)), rawDate: "2024-11-30",
    }),
  ];

  const players: Player[] = [
    { id: 1, name: "Neymar Jr", age: 31, nationality: "Brazil", overall: 92, potential: 92, club: "Paris Saint-Germain", position: "LW", jerseyNumber: 10, height: "5'9", weight: "150lbs", skills: zeroSkills() },
    { id: 2, name: "Alisson", age: 30, nationality: "Brazil", overall: 89, potential: 89, club: "Liverpool", position: "GK", jerseyNumber: 1, height: "6'3", weight: "190lbs", skills: zeroSkills() },
    { id: 3, name: "Casemiro", age: 31, nationality: "Brazil", overall: 89, potential: 89, club: "Real Madrid", position: "CDM", jerseyNumber: 14, height: "6'1", weight: "175lbs", skills: zeroSkills() },
    { id: 4, name: "L. Messi", age: 31, nationality: "Argentina", overall: 94, potential: 94, club: "FC Barcelona", position: "RF", jerseyNumber: 10, height: "5'7", weight: "159lbs", skills: zeroSkills() },
    { id: 5, name: "Gabriel Barbosa", age: 27, nationality: "Brazil", overall: 80, potential: 83, club: "Flamengo", position: "ST", jerseyNumber: 9, height: "5'11", weight: "170lbs", skills: zeroSkills() },
    { id: 6, name: "Bruno Henrique", age: 32, nationality: "Brazil", overall: 79, potential: 79, club: "Flamengo", position: "LW", jerseyNumber: 27, height: "5'10", weight: "168lbs", skills: zeroSkills() },
    { id: 7, name: "Dudu", age: 30, nationality: "Brazil", overall: 78, potential: 78, club: "Palmeiras", position: "RW", jerseyNumber: 7, height: "5'9", weight: "165lbs", skills: zeroSkills() },
  ];

  return { matches, players, counts: { matchesBySource: {}, players: players.length } };
}

function zeroSkills() {
  return {
    crossing: 0, finishing: 0, dribbling: 0, shortPassing: 0, longPassing: 0,
    shotPower: 0, stamina: 0, strength: 0, interceptions: 0, positioning: 0, vision: 0, composure: 0,
  };
}
