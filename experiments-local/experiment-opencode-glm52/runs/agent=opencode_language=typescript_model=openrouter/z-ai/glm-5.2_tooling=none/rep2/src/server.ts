import express, { type Express, type Request, type Response } from "express";
import { createDb, type DBType } from "./db";
import { createBooksRouter } from "./routes/books";
import { createHealthRouter } from "./routes/health";

export interface AppOptions {
  dbFile?: string;
}

export function createApp(options: AppOptions = {}): { app: Express; db: DBType } {
  const db = createDb(options.dbFile);
  const app = express();
  app.use(express.json());

  app.use("/health", createHealthRouter());
  app.use("/books", createBooksRouter(db));

  app.use((err: Error, _req: Request, res: Response, _next: unknown) => {
    if (err instanceof SyntaxError && "body" in err) {
      res.status(400).json({ error: "invalid JSON body" });
      return;
    }
    res.status(500).json({ error: "internal server error" });
  });

  return { app, db };
}

export function startServer(port: number = 3000): void {
  const { app, db } = createApp({ dbFile: "books.db" });
  app.listen(port, () => {
    console.log(`Books API listening on http://localhost:${port}`);
  });
  process.on("SIGINT", () => {
    db.close();
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    db.close();
    process.exit(0);
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  startServer(port);
}
