import { loadData } from "./src/loader.js";
import { SoccerStore } from "./src/store.js";
const d = loadData();
const m2019 = d.matches.filter(m=>m.season===2019 && m.competition==="Brasileirão");
console.log("2019 Brasileirão matches:", m2019.length);
const bySrc = new Map<string,number>();
for (const m of m2019) bySrc.set(m.sourceFile,(bySrc.get(m.sourceFile)??0)+1);
console.log("by source:", [...bySrc.entries()]);
const teams = new Set<string>();
for (const m of m2019) { teams.add(m.homeTeamKey); teams.add(m.awayTeamKey); }
console.log("distinct team keys 2019:", teams.size, [...teams].sort().join(", "));
const atm = m2019.filter(m=>m.homeTeamKey==="atletico-mg"||m.awayTeamKey==="atletico-mg");
console.log("atletico-mg 2019 matches:", atm.length);
const atmBySrc = new Map<string,number>();
for (const m of atm) atmBySrc.set(m.sourceFile,(atmBySrc.get(m.sourceFile)??0)+1);
console.log("atletico-mg by source:", [...atmBySrc.entries()]);
// Show first 3 atm matches with sig-relevant fields
for (const m of atm.slice(0,6)) console.log(`  ${m.sourceFile} ${m.date} ${m.homeTeamKey} ${m.homeGoal}-${m.awayGoal} ${m.awayTeamKey}`);
