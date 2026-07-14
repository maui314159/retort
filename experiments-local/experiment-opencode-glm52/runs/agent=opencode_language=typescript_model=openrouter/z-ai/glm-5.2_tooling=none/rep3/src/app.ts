import express from "express";
import type { Database as DBType } from "better-sqlite3";
import { createRouter } from "./routes.js";

export function createApp(db: DBType): express.Express {
  const app = express();
  app.use(express.json());
  app.use(createRouter(db));
  app.use((req, res) => {
    res.status(404).json({ error: "not found" });
  });
  app.use(
    (
      err: unknown,
      _req: express.Request,
      res: express.Response,
      _next: express.NextFunction
    ) => {
      if (err instanceof SyntaxError && "body" in err) {
        res.status(400).json({ error: "invalid JSON body" });
        return;
      }
      res.status(500).json({ error: "internal server error" });
    }
  );
  return app;
}
