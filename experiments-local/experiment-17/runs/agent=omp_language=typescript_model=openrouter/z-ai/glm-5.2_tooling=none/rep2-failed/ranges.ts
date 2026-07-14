import { readFileSync } from "node:fs";
import Papa from "papaparse";
import { parseDate, parseSeason } from "./src/normalize.js";
const parse = (f: string) => Papa.parse<Record<string,string>>(readFileSync(f,"utf8"), {header:true, skipEmptyLines:true}).data.filter(r=>r&&typeof r==="object");

const seasonRange = (rows: Record<string,string>[], key: string) => {
  const yrs = rows.map(r=>parseSeason(r[key])).filter((x): x is number=>x!=null).sort((a,b)=>a-b);
  return { min: yrs[0], max: yrs[yrs.length-1], n: yrs.length };
};
const dateRange = (rows: Record<string,string>[], key: string) => {
  const ds = rows.map(r=>parseDate(r[key])).filter((x): x is string=>x!=null).sort();
  return { min: ds[0], max: ds[ds.length-1], n: ds.length };
};

const bras = parse("data/kaggle/Brasileirao_Matches.csv");
const cup = parse("data/kaggle/Brazilian_Cup_Matches.csv");
const lib = parse("data/kaggle/Libertadores_Matches.csv");
const hist = parse("data/kaggle/novo_campeonato_brasileiro.csv");
const ext = parse("data/kaggle/BR-Football-Dataset.csv");

console.log("Brasileirao_Matches seasons:", seasonRange(bras,"season"));
console.log("Brazilian_Cup seasons:", seasonRange(cup,"season"));
console.log("Libertadores seasons:", seasonRange(lib,"season"));
console.log("Historical (Ano) seasons:", seasonRange(hist,"Ano"));
console.log("BR-Football date range:", dateRange(ext,"date"));
console.log("BR-Football tournaments x year:");
const m = new Map<string,number>();
for (const r of ext) { const y = parseDate(r.date)?.slice(0,4) ?? "?"; const k=`${r.tournament}|${y}`; m.set(k,(m.get(k)??0)+1); }
console.log([...m.entries()].sort().join("\n"));
