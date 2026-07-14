import express, {
  type Application,
  type Request,
  type Response,
  type NextFunction,
} from "express";
import { buildBooksRouter } from "./books.routes.js";
import { BooksRepository } from "./books.repository.js";
import type { DB } from "./db.js";

export function createApp(db: DB): Application {
  const app: Application = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok" });
  });

  const repo = new BooksRepository(db);
  app.use("/books", buildBooksRouter(repo));

  // 404 for unmatched routes
  app.use((req: Request, res: Response) => {
    res.status(404).json({ error: "not found" });
  });

  // error handler
  app.use(
    (
      err: unknown,
      _req: Request,
      res: Response,
      _next: NextFunction
    ): void => {
      if (err instanceof SyntaxError && "status" in err && err.status === 400) {
        res.status(400).json({ error: "invalid JSON body" });
        return;
      }
      console.error("unhandled error:", err);
      res.status(500).json({ error: "internal server error" });
    }
  );

  return app;
}
