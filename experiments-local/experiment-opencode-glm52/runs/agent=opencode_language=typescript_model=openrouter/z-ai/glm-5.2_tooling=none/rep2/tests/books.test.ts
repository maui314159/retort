import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import { createApp, type AppOptions } from "../src/server";

function makeApp(options: AppOptions = {}) {
  return createApp({ dbFile: ":memory:", ...options });
}

describe("Books API", () => {
  let app: ReturnType<typeof makeApp>["app"];
  let db: ReturnType<typeof makeApp>["db"];

  beforeEach(() => {
    const r = makeApp();
    app = r.app;
    db = r.db;
  });

  afterEach(() => {
    db.close();
  });

  describe("GET /health", () => {
    it("returns ok status", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: "ok" });
    });
  });

  describe("POST /books", () => {
    it("creates a book and returns 201", async () => {
      const res = await request(app).post("/books").send({
        title: "Dune",
        author: "Frank Herbert",
        year: 1965,
        isbn: "9780441172720",
      });
      expect(res.status).toBe(201);
      expect(res.body.id).toBe(1);
      expect(res.body.title).toBe("Dune");
      expect(res.body.author).toBe("Frank Herbert");
      expect(res.body.year).toBe(1965);
    });

    it("rejects missing title with 400", async () => {
      const res = await request(app).post("/books").send({
        author: "Frank Herbert",
      });
      expect(res.status).toBe(400);
      expect(res.body.errors).toBeDefined();
      const messages = res.body.errors.join(" ");
      expect(messages).toContain("title");
    });

    it("rejects missing author with 400", async () => {
      const res = await request(app).post("/books").send({
        title: "Dune",
      });
      expect(res.status).toBe(400);
      const messages = res.body.errors.join(" ");
      expect(messages).toContain("author");
    });

    it("accepts optional fields as null", async () => {
      const res = await request(app)
        .post("/books")
        .send({ title: "Foo", author: "Bar", year: null, isbn: null });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe("GET /books", () => {
    beforeEach(async () => {
      await request(app).post("/books").send({
        title: "Dune",
        author: "Frank Herbert",
        year: 1965,
      });
      await request(app).post("/books").send({
        title: "1984",
        author: "George Orwell",
        year: 1949,
      });
      await request(app).post("/books").send({
        title: "Thetogartle",
        author: "Frank Herbert",
      });
    });

    it("lists all books", async () => {
      const res = await request(app).get("/books");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
    });

    it("filters by author", async () => {
      const res = await request(app).get("/books?author=Frank Herbert");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(
        res.body.every(
          (b: { author: string }) => b.author === "Frank Herbert",
        ),
      ).toBe(true);
    });
  });

  describe("GET /books/:id", () => {
    it("returns a book by id", async () => {
      const created = await request(app).post("/books").send({
        title: "Dune",
        author: "Frank Herbert",
      });
      const id = created.body.id;
      const res = await request(app).get(`/books/${id}`);
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(id);
      expect(res.body.title).toBe("Dune");
    });

    it("returns 404 for unknown id", async () => {
      const res = await request(app).get("/books/9999");
      expect(res.status).toBe(404);
    });
  });

  describe("PUT /books/:id", () => {
    it("updates an existing book", async () => {
      const created = await request(app).post("/books").send({
        title: "Dune",
        author: "Frank Herbert",
      });
      const id = created.body.id;
      const res = await request(app)
        .put(`/books/${id}`)
        .send({ title: "Dune Updated", author: "Frank H.", year: 1970 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("Dune Updated");
      expect(res.body.author).toBe("Frank H.");
      expect(res.body.year).toBe(1970);
    });

    it("returns 404 when updating missing book", async () => {
      const res = await request(app)
        .put("/books/8888")
        .send({ title: "X", author: "Y" });
      expect(res.status).toBe(404);
    });

    it("rejects invalid update body", async () => {
      const created = await request(app).post("/books").send({
        title: "Dune",
        author: "Frank Herbert",
      });
      const id = created.body.id;
      const res = await request(app).put(`/books/${id}`).send({ title: "" });
      expect(res.status).toBe(400);
    });
  });

  describe("DELETE /books/:id", () => {
    it("deletes a book and returns 204", async () => {
      const created = await request(app).post("/books").send({
        title: "Dune",
        author: "Frank Herbert",
      });
      const id = created.body.id;
      const res = await request(app).delete(`/books/${id}`);
      expect(res.status).toBe(204);
      const follow = await request(app).get(`/books/${id}`);
      expect(follow.status).toBe(404);
    });

    it("returns 404 for deleting missing book", async () => {
      const res = await request(app).delete("/books/7777");
      expect(res.status).toBe(404);
    });
  });
});
