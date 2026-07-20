import express, { Express, Request, Response } from "express";
import { BookStore } from "./db";
import { BookInput } from "./types";

interface ValidationError {
  errors: string[];
}

function validateBookPayload(body: unknown): BookInput | ValidationError {
  const errors: string[] = [];

  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return { errors: ["Request body must be a JSON object"] };
  }

  const { title, author, year, isbn } = body as Record<string, unknown>;

  if (typeof title !== "string" || title.trim().length === 0) {
    errors.push("title is required and must be a non-empty string");
  }
  if (typeof author !== "string" || author.trim().length === 0) {
    errors.push("author is required and must be a non-empty string");
  }
  if (year !== undefined && year !== null) {
    if (typeof year !== "number" || !Number.isInteger(year)) {
      errors.push("year must be an integer");
    }
  }
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") {
    errors.push("isbn must be a string");
  }

  if (errors.length > 0) {
    return { errors };
  }

  return {
    title: (title as string).trim(),
    author: (author as string).trim(),
    year: (year as number | null | undefined) ?? null,
    isbn: (isbn as string | null | undefined) ?? null,
  };
}

function isValidationError(
  result: BookInput | ValidationError
): result is ValidationError {
  return "errors" in result;
}

function parseId(raw: string): number | null {
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) {
    return null;
  }
  return id;
}

export function createApp(store: BookStore): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const parsed = validateBookPayload(req.body);
    if (isValidationError(parsed)) {
      res.status(400).json({ errors: parsed.errors });
      return;
    }
    const book = store.create(parsed);
    res.status(201).json(book);
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author;
    const books = store.list(typeof author === "string" ? author : undefined);
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const book = store.getById(id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const parsed = validateBookPayload(req.body);
    if (isValidationError(parsed)) {
      res.status(400).json({ errors: parsed.errors });
      return;
    }
    const book = store.update(id, parsed);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    if (!store.delete(id)) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  // JSON parse errors and unknown-body-type errors land here.
  app.use(
    (
      err: unknown,
      _req: Request,
      res: Response,
      _next: express.NextFunction
    ) => {
      if (
        err instanceof SyntaxError ||
        (typeof err === "object" &&
          err !== null &&
          "status" in err &&
          (err as { status: number }).status === 400)
      ) {
        res.status(400).json({ error: "invalid JSON body" });
        return;
      }
      res.status(500).json({ error: "internal server error" });
    }
  );

  return app;
}
