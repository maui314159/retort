import { getDataStore, teamMatches } from "../data-loader.js";

export function getAggregateStats(params: { competition?: string; season?: number }): string {
  const { matches } = getDataStore();

  let filtered = matches.filter((m) => {
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if ((comp.includes("brasileirao") || comp.includes("serie a")) && m.competition !== "brasileirao" && m.competition !== "historical") return false;
      if (comp.includes("copa do brasil") && m.competition !== "copa_do_brasil") return false;
      if (comp.includes("libertadores") && m.competition !== "libertadores") return false;
    }
    if (params.season && m.season !== params.season) return false;
    return true;
  });

  if (filtered.length === 0) return "No matches found for the given criteria.";

  let homeWins = 0, awayWins = 0, draws = 0;
  let totalGoals = 0;
  let highestScoring = filtered[0];
  let lowestScoring = filtered[0];

  for (const m of filtered) {
    totalGoals += m.homeGoals + m.awayGoals;
    const total = m.homeGoals + m.awayGoals;
    if (total > (highestScoring.homeGoals + highestScoring.awayGoals)) highestScoring = m;
    if (total < (lowestScoring.homeGoals + lowestScoring.awayGoals)) lowestScoring = m;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }

  const total = filtered.length;
  const avgGoals = (totalGoals / total).toFixed(2);
  const homeWinRate = ((homeWins / total) * 100).toFixed(1);
  const awayWinRate = ((awayWins / total) * 100).toFixed(1);
  const drawRate = ((draws / total) * 100).toFixed(1);

  const context = [
    params.competition ?? "All competitions",
    params.season ? `Season ${params.season}` : "All seasons",
  ].join(", ");

  return [
    `Aggregate Statistics (${context})`,
    `Total Matches: ${total}`,
    `Total Goals: ${totalGoals}`,
    `Average Goals/Match: ${avgGoals}`,
    `Home Wins: ${homeWins} (${homeWinRate}%)`,
    `Away Wins: ${awayWins} (${awayWinRate}%)`,
    `Draws: ${draws} (${drawRate}%)`,
    `Highest Scoring Match: ${highestScoring.homeTeam} ${highestScoring.homeGoals}-${highestScoring.awayGoals} ${highestScoring.awayTeam} (${highestScoring.homeGoals + highestScoring.awayGoals} goals)`,
  ].join("\n");
}

export function getSeasonComparison(params: { season1: number; season2: number; competition?: string }): string {
  const { matches } = getDataStore();

  const getSeasonStats = (season: number) => {
    const filtered = matches.filter((m) => {
      if (m.season !== season) return false;
      if (params.competition) {
        const comp = params.competition.toLowerCase();
        if ((comp.includes("brasileirao") || comp.includes("serie a")) && m.competition !== "brasileirao" && m.competition !== "historical") return false;
      } else {
        if (m.competition !== "brasileirao" && m.competition !== "historical") return false;
      }
      return true;
    });

    const goals = filtered.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
    const homeWins = filtered.filter((m) => m.homeGoals > m.awayGoals).length;
    const teams = new Set([...filtered.map((m) => m.homeTeam), ...filtered.map((m) => m.awayTeam)]);

    return {
      season,
      matches: filtered.length,
      goals,
      avgGoals: filtered.length > 0 ? (goals / filtered.length).toFixed(2) : "0",
      homeWinRate: filtered.length > 0 ? ((homeWins / filtered.length) * 100).toFixed(1) : "0",
      teams: teams.size,
    };
  };

  const s1 = getSeasonStats(params.season1);
  const s2 = getSeasonStats(params.season2);

  if (s1.matches === 0 && s2.matches === 0) {
    return `No data found for seasons ${params.season1} or ${params.season2}.`;
  }

  const comp = params.competition ?? "Brasileirão";

  const formatRow = (label: string, v1: string | number, v2: string | number) =>
    `${label.padEnd(22)} ${String(v1).padStart(10)}   ${String(v2).padStart(10)}`;

  return [
    `${comp} Season Comparison`,
    formatRow("", params.season1, params.season2),
    "-".repeat(47),
    formatRow("Matches", s1.matches, s2.matches),
    formatRow("Total Goals", s1.goals, s2.goals),
    formatRow("Avg Goals/Match", s1.avgGoals, s2.avgGoals),
    formatRow("Home Win Rate", `${s1.homeWinRate}%`, `${s2.homeWinRate}%`),
    formatRow("Teams", s1.teams, s2.teams),
  ].join("\n");
}

export function getMostGoals(params: { competition?: string; season?: number; limit?: number }): string {
  const { matches } = getDataStore();
  const limit = params.limit ?? 10;

  let filtered = matches.filter((m) => {
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if ((comp.includes("brasileirao") || comp.includes("serie a")) && m.competition !== "brasileirao" && m.competition !== "historical") return false;
      if (comp.includes("copa do brasil") && m.competition !== "copa_do_brasil") return false;
      if (comp.includes("libertadores") && m.competition !== "libertadores") return false;
    }
    if (params.season && m.season !== params.season) return false;
    return true;
  });

  // Goals scored by team
  const teamGoals = new Map<string, number>();
  for (const m of filtered) {
    const hk = m.homeTeam.toLowerCase();
    const ak = m.awayTeam.toLowerCase();
    teamGoals.set(hk, (teamGoals.get(hk) ?? 0) + m.homeGoals);
    teamGoals.set(ak, (teamGoals.get(ak) ?? 0) + m.awayGoals);
  }

  // Get display name for each team key
  const teamNames = new Map<string, string>();
  for (const m of filtered) {
    teamNames.set(m.homeTeam.toLowerCase(), m.homeTeam);
    teamNames.set(m.awayTeam.toLowerCase(), m.awayTeam);
  }

  const sorted = Array.from(teamGoals.entries())
    .map(([key, goals]) => ({ team: teamNames.get(key) ?? key, goals }))
    .sort((a, b) => b.goals - a.goals)
    .slice(0, limit);

  const context = [
    params.competition ?? "All competitions",
    params.season ? `Season ${params.season}` : "All seasons",
  ].join(", ");

  const lines = sorted.map((t, i) => `${i + 1}. ${t.team}: ${t.goals} goals`);
  return [`Top Goal-Scoring Teams (${context})`, ...lines].join("\n");
}
