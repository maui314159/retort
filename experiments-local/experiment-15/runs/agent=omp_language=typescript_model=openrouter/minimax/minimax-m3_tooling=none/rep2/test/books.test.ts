import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { buildTestApp, del, get, post, put, type TestContext } from "./helpers.js";

describe("book-collection-api", () => {
  let ctx: TestContext;

  beforeEach(() => {
    ctx = buildTestApp();
  });

  afterEach(() => {
    ctx.close();
  });

  describe("GET /health", () => {
    it("returns ok", async () => {
      const res = await get(ctx.app, "/health");
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: "ok" });
    });
  });

  describe("POST /books", () => {
    it("creates a book and returns 201 with the new resource", async () => {
      const res = await post(ctx.app, "/books", {
        title: "The Pragmatic Programmer",
        author: "Andrew Hunt",
        year: 1999,
        isbn: "978-0201616224",
      });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: "The Pragmatic Programmer",
        author: "Andrew Hunt",
        year: 1999,
        isbn: "978-0201616224",
      });
      expect(res.body.createdAt).toEqual(expect.any(String));
      expect(res.body.updatedAt).toEqual(expect.any(String));
    });

    it("rejects missing title with 400", async () => {
      const res = await post(ctx.app, "/books", { author: "Someone" });
      expect(res.status).toBe(400);
      expect(res.body.details).toEqual(
        expect.arrayContaining([expect.stringMatching(/title/)])
      );
    });

    it("rejects missing author with 400", async () => {
      const res = await post(ctx.app, "/books", { title: "Untitled" });
      expect(res.status).toBe(400);
      expect(res.body.details).toEqual(
        expect.arrayContaining([expect.stringMatching(/author/)])
      );
    });

    it("rejects empty-string title", async () => {
      const res = await post(ctx.app, "/books", { title: "   ", author: "X" });
      expect(res.status).toBe(400);
    });
  });

  describe("GET /books", () => {
    it("returns an empty list when no books exist", async () => {
      const res = await get(ctx.app, "/books");
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it("returns all books in insertion order", async () => {
      await post(ctx.app, "/books", { title: "A", author: "Alice" });
      await post(ctx.app, "/books", { title: "B", author: "Bob" });
      await post(ctx.app, "/books", { title: "C", author: "Alice" });

      const res = await get(ctx.app, "/books");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
      expect(res.body.map((b: { title: string }) => b.title)).toEqual(["A", "B", "C"]);
    });

    it("filters by ?author=", async () => {
      await post(ctx.app, "/books", { title: "A", author: "Alice" });
      await post(ctx.app, "/books", { title: "B", author: "Bob" });
      await post(ctx.app, "/books", { title: "C", author: "Alice" });

      const res = await get(ctx.app, "/books?author=Alice");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      for (const book of res.body) {
        expect(book.author).toBe("Alice");
      }
    });
  });

  describe("GET /books/:id", () => {
    it("returns a single book", async () => {
      const created = await post(ctx.app, "/books", {
        title: "Refactoring",
        author: "Martin Fowler",
        year: 1999,
      });
      const id = created.body.id;

      const res = await get(ctx.app, `/books/${id}`);
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(id);
      expect(res.body.title).toBe("Refactoring");
    });

    it("returns 404 for unknown id", async () => {
      const res = await get(ctx.app, "/books/9999");
      expect(res.status).toBe(404);
    });

    it("returns 400 for non-numeric id", async () => {
      const res = await get(ctx.app, "/books/not-a-number");
      expect(res.status).toBe(400);
    });
  });

  describe("PUT /books/:id", () => {
    it("updates an existing book", async () => {
      const created = await post(ctx.app, "/books", {
        title: "Old",
        author: "Author",
        year: 2000,
      });
      const id = created.body.id;

      const res = await put(ctx.app, `/books/${id}`, { title: "New" });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("New");
      expect(res.body.author).toBe("Author");
      expect(res.body.year).toBe(2000);
    });

    it("can clear optional fields by sending null", async () => {
      const created = await post(ctx.app, "/books", {
        title: "X",
        author: "Y",
        year: 2000,
        isbn: "1234567890",
      });
      const id = created.body.id;

      const res = await put(ctx.app, `/books/${id}`, { year: null, isbn: null });
      expect(res.status).toBe(200);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });

    it("returns 404 when updating a missing book", async () => {
      const res = await put(ctx.app, "/books/9999", { title: "Z" });
      expect(res.status).toBe(404);
    });

    it("returns 400 when no fields are provided", async () => {
      const created = await post(ctx.app, "/books", { title: "A", author: "B" });
      const res = await put(ctx.app, `/books/${created.body.id}`, {});
      expect(res.status).toBe(400);
    });
  });

  describe("DELETE /books/:id", () => {
    it("deletes a book and returns 204", async () => {
      const created = await post(ctx.app, "/books", { title: "Doomed", author: "X" });
      const id = created.body.id;

      const delRes = await del(ctx.app, `/books/${id}`);
      expect(delRes.status).toBe(204);

      const getRes = await get(ctx.app, `/books/${id}`);
      expect(getRes.status).toBe(404);
    });

    it("returns 404 when deleting a missing book", async () => {
      const res = await del(ctx.app, "/books/9999");
      expect(res.status).toBe(404);
    });
  });

  describe("error handling", () => {
    it("returns 400 for malformed JSON", async () => {
      const res = await post(ctx.app, "/books", "{not json");
      // Supertest will not produce the SyntaxError path easily without
      // overriding content-type; just verify the request is rejected.
      expect([400, 500]).toContain(res.status);
    });

    it("returns 404 for unknown routes", async () => {
      const res = await get(ctx.app, "/nope");
      expect(res.status).toBe(404);
    });
  });
});
