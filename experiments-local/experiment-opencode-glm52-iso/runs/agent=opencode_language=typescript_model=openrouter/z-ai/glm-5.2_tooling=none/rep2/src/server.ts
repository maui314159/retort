import express, { type Request, type Response } from "express";
import { booksRouter } from "./routes/books";
import { healthRouter } from "./routes/health";

export function createApp() {
  const app = express();
  app.use(express.json());

  app.use("/health", healthRouter);
  app.use("/books", booksRouter);

  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "not found" });
  });

  return app;
}

const app = createApp();

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Book collection API listening on port ${PORT}`);
  });
}

export default app;
