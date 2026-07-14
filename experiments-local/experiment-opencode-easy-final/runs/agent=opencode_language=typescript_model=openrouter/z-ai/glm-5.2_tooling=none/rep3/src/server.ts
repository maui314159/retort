import express, {
  type Request,
  type Response,
  type ErrorRequestHandler,
} from "express";
import { booksRouter } from "./books.js";
import { healthRouter } from "./health.js";
import { closeDb } from "./db.js";

export function createApp(): express.Application {
  const app = express();
  app.use(express.json());

  app.use("/health", healthRouter);
  app.use("/books", booksRouter);

  app.use((req: Request, res: Response) => {
    res.status(404).json({ message: `Route not found: ${req.method} ${req.originalUrl}` });
  });

  const errHandler: ErrorRequestHandler = (err, _req, res, _next) => {
    res
      .status(500)
      .json({ message: "Internal server error", error: (err as Error).message });
  };
  app.use(errHandler);
  return app;
}

const app = createApp();

const port = Number.parseInt(process.env.PORT ?? "3000", 10);
const server = app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`Book API listening on http://localhost:${port}`);
});

const shutdown = () => {
  server.close(() => {
    closeDb();
    process.exit(0);
  });
  setTimeout(() => process.exit(0), 5000).unref();
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

export { app };
