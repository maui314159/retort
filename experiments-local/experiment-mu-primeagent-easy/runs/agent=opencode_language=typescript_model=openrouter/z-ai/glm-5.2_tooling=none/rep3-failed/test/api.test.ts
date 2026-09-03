import request from "supertest";
import { expect } from "chai";
import { createApp } from "../src/app";

describe("Book API", () => {
  const { app } = createApp({ dbPath: ":memory:" });

  it("POST /books creates a book and returns 201 with the book", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "1234" })
      .expect(201);

    expect(res.body.id).to.be.a("number");
    expect(res.body.title).to.equal("Dune");
    expect(res.body.author).to.equal("Frank Herbert");
    expect(res.body.year).to.equal(1965);
    expect(res.body.isbn).to.equal("1234");
  });

  it("POST /books rejects missing title with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ author: "No Title" })
      .expect(400);
    expect(res.body.error).to.match(/title/);
  });

  it("POST /books rejects missing author with 400", async () => {
    await request(app)
      .post("/books")
      .send({ title: "No Author" })
      .expect(400);
  });

  it("GET /books lists all books", async () => {
    await request(app).post("/books").send({ title: "A", author: "X" });
    await request(app).post("/books").send({ title: "B", author: "Y" });
    const res = await request(app).get("/books").expect(200);
    expect(res.body).to.be.an("array");
    expect(res.body.length).to.be.greaterThan(1);
  });

  it("GET /books?author= filters by author", async () => {
    await request(app).post("/books").send({ title: "T1", author: "UniqueAuthor" });
    const res = await request(app)
      .get("/books?author=UniqueAuthor")
      .expect(200);
    expect(res.body).to.be.an("array");
    expect(res.body.length).to.equal(1);
    expect(res.body[0].author).to.equal("UniqueAuthor");
  });

  it("GET /books/{id} returns the book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "ById", author: "Z" })
      .expect(201);
    const res = await request(app)
      .get(`/books/${created.body.id}`)
      .expect(200);
    expect(res.body.title).to.equal("ById");
  });

  it("GET /books/{id} returns 404 for unknown id", async () => {
    await request(app).get("/books/999999").expect(404);
  });

  it("PUT /books/{id} updates a book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Old", author: "OldA" })
      .expect(201);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "New", author: "NewA", year: 2000 })
      .expect(200);
    expect(res.body.title).to.equal("New");
    expect(res.body.author).to.equal("NewA");
    expect(res.body.year).to.equal(2000);
  });

  it("DELETE /books/{id} removes a book and returns 204", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Delete", author: "D" })
      .expect(201);
    await request(app).delete(`/books/${created.body.id}`).expect(204);
    await request(app).get(`/books/${created.body.id}`).expect(404);
  });

  it("GET /health returns 200 ok", async () => {
    const res = await request(app).get("/health").expect(200);
    expect(res.body.status).to.equal("ok");
  });
});
