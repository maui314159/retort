import express, { Express } from "express";
import healthRouter from "./routes/health";
import booksRouter from "./routes/books";

/**
 * Create and configure the Express application.
 * Exported so tests can import it without starting the server.
 */
export function createApp(): Express {
  const app = express();

  app.use(express.json());

  // Health check
  app.use("/health", healthRouter);

  // Book routes
  app.use("/books", booksRouter);

  // 404 handler for unmatched routes
  app.use((_req, res) => {
    res.status(404).json({ error: "Not found" });
  });

  return app;
}
