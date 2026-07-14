import { Router } from "express";
import { BooksRepository } from "./books.repository.js";
import { bookCreateSchema, bookUpdateSchema } from "./validation.js";

function parseId(raw: string): number | null {
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function buildBooksRouter(repo: BooksRepository): Router {
  const router = Router();

  router.post("/", (req, res) => {
    const parsed = bookCreateSchema.safeParse(req.body);
    if (!parsed.success) {
      return res
        .status(400)
        .json({ errors: parsed.error.flatten().fieldErrors });
    }
    const book = repo.create(parsed.data);
    return res.status(201).json(book);
  });

  router.get("/", (req, res) => {
    const authorQuery = req.query.author;
    const author =
      typeof authorQuery === "string" && authorQuery.length > 0
        ? authorQuery
        : undefined;
    const books = repo.list(author ? { author } : undefined);
    return res.json(books);
  });

  router.get("/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid id" });
    const book = repo.getById(id);
    if (!book) return res.status(404).json({ error: "not found" });
    return res.json(book);
  });

  router.put("/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid id" });
    const parsed = bookUpdateSchema.safeParse(req.body);
    if (!parsed.success) {
      return res
        .status(400)
        .json({ errors: parsed.error.flatten().fieldErrors });
    }
    if (Object.keys(parsed.data).length === 0) {
      return res.status(400).json({ error: "no fields to update" });
    }
    const book = repo.update(id, parsed.data);
    if (!book) return res.status(404).json({ error: "not found" });
    return res.json(book);
  });

  router.delete("/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid id" });
    const ok = repo.delete(id);
    if (!ok) return res.status(404).json({ error: "not found" });
    return res.status(204).send();
  });

  return router;
}
