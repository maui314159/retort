import { readFileSync } from "node:fs";
import Papa from "papaparse";
import { parseDate, parseSeason, teamKey, teamDisplay, toInt } from "./src/normalize.js";

const parse = (f: string) => Papa.parse<Record<string,string>>(readFileSync(f,"utf8"), {header:true, skipEmptyLines:true}).data.filter(r=>r&&typeof r==="object");

const modern = parse("data/kaggle/Brasileirao_Matches.csv").filter(r=>parseSeason(r.season)===2019).slice(0,3);
console.log("=== modern 2019 sample ===");
for (const r of modern) console.log(JSON.stringify({home:r.home_team, away:r.away_team, hg:r.home_goal, ag:r.away_goal, date:parseDate(r.datetime), hk:teamKey(r.home_team), ak:teamKey(r.away_team)}));

const hist = parse("data/kaggle/novo_campeonato_brasileiro.csv").filter(r=>parseSeason(r.Ano)===2019).slice(0,5);
console.log("=== historical 2019 sample ===");
for (const r of hist) console.log(JSON.stringify({home:r.Equipe_mandante, away:r.Equipe_visitante, hg:r.Gols_mandante, ag:r.Gols_visitante, date:parseDate(r.Data), hk:teamKey(r.Equipe_mandante), ak:teamKey(r.Equipe_visitante)}));

// Count 2019 per file
const m19 = parse("data/kaggle/Brasileirao_Matches.csv").filter(r=>parseSeason(r.season)===2019).length;
const h19 = parse("data/kaggle/novo_campeonato_brasileiro.csv").filter(r=>parseSeason(r.Ano)===2019).length;
console.log("modern 2019:", m19, "historical 2019:", h19);

// Try to find a matching pair: same date, same home key, same away key
const mod19 = parse("data/kaggle/Brasileirao_Matches.csv").filter(r=>parseSeason(r.season)===2019);
const hi19 = parse("data/kaggle/novo_campeonato_brasileiro.csv").filter(r=>parseSeason(r.Ano)===2019);
const msigs = new Set(mod19.map(r=>`Brasileirão|${parseDate(r.datetime)}|${teamKey(r.home_team)}|${teamKey(r.away_team)}|${toInt(r.home_goal)}|${toInt(r.away_goal)}`));
let matched=0;
for (const r of hi19) {
  const s = `Brasileirão|${parseDate(r.Data)}|${teamKey(r.Equipe_mandante)}|${teamKey(r.Equipe_visitante)}|${toInt(r.Gols_mandante)}|${toInt(r.Gols_visitante)}`;
  if (msigs.has(s)) matched++;
}
console.log("historical 2019 rows matching a modern sig:", matched, "of", hi19.length);
// Show a non-matching historical example with its modern counterpart by date
const byKey = new Map(mod19.map(r=>[`${parseDate(r.datetime)}|${teamKey(r.home_team)}|${teamKey(r.away_team)}`, r]));
for (const r of hi19.slice(0,3)) {
  const k = `${parseDate(r.Data)}|${teamKey(r.Equipe_mandante)}|${teamKey(r.Equipe_visitante)}`;
  const m = byKey.get(k);
  console.log("hist:", r.Equipe_mandante, r.Gols_mandante, "x", r.Gols_visitante, r.Equipe_visitante, "-> modern match by date+keys:", m?`${m.home_team} ${m.home_goal}-${m.away_goal} ${m.away_team}`:"NONE", "| hist date:", parseDate(r.Data), "modern date:", m?parseDate(m.datetime):null);
}
