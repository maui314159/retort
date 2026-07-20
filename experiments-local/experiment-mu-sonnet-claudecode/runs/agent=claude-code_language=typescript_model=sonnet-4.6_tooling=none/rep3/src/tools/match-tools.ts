import { getDataStore, teamMatches } from "../data-loader.js";
import type { Match } from "../types.js";

const COMPETITION_LABELS: Record<string, string> = {
  brasileirao: "Brasileirão Serie A",
  copa_do_brasil: "Copa do Brasil",
  libertadores: "Copa Libertadores",
  extended: "Brazilian Football",
  historical: "Brasileirão (Historical)",
};

function formatMatch(m: Match): string {
  const date = m.datetime ? m.datetime.toISOString().split("T")[0] : "Unknown date";
  const comp = COMPETITION_LABELS[m.competition] ?? m.competition;
  const context = m.stage ?? m.round ?? m.tournament ?? "";
  const contextStr = context ? ` (${comp} - ${context})` : ` (${comp})`;
  return `${date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}${contextStr}`;
}

export function searchMatches(params: {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  team2?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}): string {
  const { matches } = getDataStore();
  const limit = params.limit ?? 50;

  let filtered = matches.filter((m) => {
    if (params.homeTeam && !teamMatches(m.homeTeam, params.homeTeam)) return false;
    if (params.awayTeam && !teamMatches(m.awayTeam, params.awayTeam)) return false;
    if (params.team && !teamMatches(m.homeTeam, params.team) && !teamMatches(m.awayTeam, params.team)) return false;
    if (params.team2) {
      const t1 = params.team ?? params.homeTeam ?? params.awayTeam ?? "";
      const matchesTeam2AsHome = teamMatches(m.homeTeam, params.team2);
      const matchesTeam2AsAway = teamMatches(m.awayTeam, params.team2);
      if (!matchesTeam2AsHome && !matchesTeam2AsAway) return false;
      if (t1) {
        const matchesT1AsHome = teamMatches(m.homeTeam, t1);
        const matchesT1AsAway = teamMatches(m.awayTeam, t1);
        if (!matchesT1AsHome && !matchesT1AsAway) return false;
      }
    }
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if (comp.includes("brasileirao") || comp.includes("serie a")) {
        if (m.competition !== "brasileirao" && m.competition !== "historical") return false;
      } else if (comp.includes("copa do brasil") || comp.includes("cup")) {
        if (m.competition !== "copa_do_brasil") return false;
      } else if (comp.includes("libertadores")) {
        if (m.competition !== "libertadores") return false;
      }
    }
    if (params.season && m.season !== params.season) return false;
    if (params.dateFrom && m.datetime && m.datetime < new Date(params.dateFrom)) return false;
    if (params.dateTo && m.datetime && m.datetime > new Date(params.dateTo)) return false;
    return true;
  });

  filtered.sort((a, b) => {
    if (!a.datetime && !b.datetime) return 0;
    if (!a.datetime) return 1;
    if (!b.datetime) return -1;
    return b.datetime.getTime() - a.datetime.getTime();
  });

  const total = filtered.length;
  const shown = filtered.slice(0, limit);

  if (shown.length === 0) return "No matches found for the given criteria.";

  const lines = shown.map(formatMatch);
  const suffix = total > limit ? `\n\n(Showing ${limit} of ${total} matches)` : `\n\nTotal: ${total} matches`;
  return lines.join("\n") + suffix;
}

export function getHeadToHead(params: { team1: string; team2: string; competition?: string; season?: number }): string {
  const { matches } = getDataStore();

  const h2hMatches = matches.filter((m) => {
    const t1Home = teamMatches(m.homeTeam, params.team1);
    const t1Away = teamMatches(m.awayTeam, params.team1);
    const t2Home = teamMatches(m.homeTeam, params.team2);
    const t2Away = teamMatches(m.awayTeam, params.team2);
    const isH2H = (t1Home && t2Away) || (t1Away && t2Home);
    if (!isH2H) return false;
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if (comp.includes("brasileirao") && m.competition !== "brasileirao" && m.competition !== "historical") return false;
      if (comp.includes("copa do brasil") && m.competition !== "copa_do_brasil") return false;
      if (comp.includes("libertadores") && m.competition !== "libertadores") return false;
    }
    if (params.season && m.season !== params.season) return false;
    return true;
  });

  h2hMatches.sort((a, b) => {
    if (!a.datetime && !b.datetime) return 0;
    if (!a.datetime) return 1;
    if (!b.datetime) return -1;
    return b.datetime.getTime() - a.datetime.getTime();
  });

  let t1Wins = 0, t2Wins = 0, draws = 0;

  for (const m of h2hMatches) {
    const t1IsHome = teamMatches(m.homeTeam, params.team1);
    if (m.homeGoals > m.awayGoals) {
      if (t1IsHome) t1Wins++; else t2Wins++;
    } else if (m.homeGoals < m.awayGoals) {
      if (t1IsHome) t2Wins++; else t1Wins++;
    } else {
      draws++;
    }
  }

  if (h2hMatches.length === 0) {
    return `No head-to-head matches found between ${params.team1} and ${params.team2}.`;
  }

  const lines = h2hMatches.slice(0, 30).map(formatMatch);
  const suffix = h2hMatches.length > 30 ? `\n...and ${h2hMatches.length - 30} more matches` : "";

  return [
    `Head-to-head: ${params.team1} vs ${params.team2}`,
    `Record: ${params.team1} ${t1Wins}W - ${draws}D - ${t2Wins}W ${params.team2}`,
    `Total matches: ${h2hMatches.length}`,
    "",
    "Recent matches:",
    ...lines,
    suffix,
  ]
    .filter((l) => l !== undefined)
    .join("\n");
}

export function getBiggestWins(params: { competition?: string; season?: number; limit?: number }): string {
  const { matches } = getDataStore();
  const limit = params.limit ?? 10;

  let filtered = matches.filter((m) => {
    if (params.competition) {
      const comp = params.competition.toLowerCase();
      if (comp.includes("brasileirao") && m.competition !== "brasileirao" && m.competition !== "historical") return false;
      if (comp.includes("copa do brasil") && m.competition !== "copa_do_brasil") return false;
      if (comp.includes("libertadores") && m.competition !== "libertadores") return false;
    }
    if (params.season && m.season !== params.season) return false;
    return true;
  });

  filtered.sort((a, b) => {
    const diffB = Math.abs(b.homeGoals - b.awayGoals);
    const diffA = Math.abs(a.homeGoals - a.awayGoals);
    if (diffB !== diffA) return diffB - diffA;
    return (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals);
  });

  const top = filtered.slice(0, limit);
  if (top.length === 0) return "No matches found.";

  const lines = top.map((m, i) => {
    const diff = Math.abs(m.homeGoals - m.awayGoals);
    return `${i + 1}. ${formatMatch(m)} (margin: ${diff})`;
  });

  return `Biggest wins:\n${lines.join("\n")}`;
}
