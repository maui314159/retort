import { Router, type Request, type Response, type NextFunction } from "express";
import { BookRepository } from "../books.js";
import { bookCreateSchema, bookUpdateSchema } from "../validation.js";

export function booksRouter(repo: BookRepository): Router {
  const router = Router();

  // POST /books
  router.post("/", (req: Request, res: Response, next: NextFunction) => {
    try {
      const parsed = bookCreateSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          error: "ValidationError",
          details: parsed.error.flatten(),
        });
      }
      const book = repo.create(parsed.data);
      return res.status(201).json(book);
    } catch (err) {
      return next(err);
    }
  });

  // GET /books?author=
  router.get("/", (req: Request, res: Response, next: NextFunction) => {
    try {
      const raw = req.query.author;
      const author =
        typeof raw === "string" && raw.trim().length > 0
          ? raw.trim()
          : undefined;
      const books = repo.findAll({ author });
      return res.status(200).json(books);
    } catch (err) {
      return next(err);
    }
  });

  // GET /books/:id
  router.get("/:id", (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = parseId(req);
      if (id === null) {
        return res.status(400).json({ error: "BadRequest", message: "id must be a positive integer" });
      }
      const book = repo.findById(id);
      if (!book) {
        return res.status(404).json({ error: "NotFound", message: `book ${id} not found` });
      }
      return res.status(200).json(book);
    } catch (err) {
      return next(err);
    }
  });

  // PUT /books/:id
  router.put("/:id", (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = parseId(req);
      if (id === null) {
        return res.status(400).json({ error: "BadRequest", message: "id must be a positive integer" });
      }
      const parsed = bookUpdateSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({
          error: "ValidationError",
          details: parsed.error.flatten(),
        });
      }
      const book = repo.update(id, parsed.data);
      if (!book) {
        return res.status(404).json({ error: "NotFound", message: `book ${id} not found` });
      }
      return res.status(200).json(book);
    } catch (err) {
      return next(err);
    }
  });

  // DELETE /books/:id
  router.delete("/:id", (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = parseId(req);
      if (id === null) {
        return res.status(400).json({ error: "BadRequest", message: "id must be a positive integer" });
      }
      const ok = repo.delete(id);
      if (!ok) {
        return res.status(404).json({ error: "NotFound", message: `book ${id} not found` });
      }
      return res.status(204).end();
    } catch (err) {
      return next(err);
    }
  });

  return router;
}

function parseId(req: Request): number | null {
  const raw = req.params.id;
  if (typeof raw !== "string") return null;
  if (!/^[0-9]+$/.test(raw)) return null;
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}
