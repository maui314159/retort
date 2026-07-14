import { readFileSync } from "node:fs";
import Papa from "papaparse";
const parse = (f: string) => Papa.parse<Record<string,string>>(readFileSync(f,"utf8"), {header:true, skipEmptyLines:true}).data.filter(r=>r&&typeof r==="object");
const uniq = (arr:string[]) => [...new Set(arr)].sort();

const bras = parse("data/kaggle/Brasileirao_Matches.csv");
console.log("=== modern Atletico/America/Botafogo names ===");
console.log(uniq([...bras.map(r=>r.home_team), ...bras.map(r=>r.away_team)]).filter(n=>/atlet|am[ée]ric|botafogo|nacional/i.test(n)).join("\n"));

const ext = parse("data/kaggle/BR-Football-Dataset.csv");
console.log("=== BR-Football Atletico/America/Botafogo/Nacional names ===");
console.log(uniq([...ext.map(r=>r.home), ...ext.map(r=>r.away)]).filter(n=>/atlet|am[ée]ric|botafogo|nacional|athlet/i.test(n)).join("\n"));

const hist = parse("data/kaggle/novo_campeonato_brasileiro.csv");
console.log("=== historical Atletico/America/Botafogo (name + UF) ===");
for (const r of hist) { for (const t of [r.Equipe_mandante, r.Equipe_visitante]) { if (/atlet|am[ée]ric|botafogo/i.test(t||"")) { console.log(t, "| UF:", r.Mandante_UF, r.Visitante_UF); } } }
