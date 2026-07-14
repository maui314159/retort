import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadAllData } from "./loader.js";
import { SoccerEngine } from "./engine.js";
import { runServer } from "./server.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(__dirname, "../data/kaggle");

const { matches, players } = await loadAllData(dataDir);
const engine = new SoccerEngine(matches, players);

await runServer(engine);
