"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const supertest_1 = __importDefault(require("supertest"));
const app_1 = require("./app");
const db_1 = require("./db");
function freshApp() {
    const store = new db_1.BookStore(":memory:");
    return (0, app_1.createApp)(store);
}
(0, node_test_1.test)("GET /health returns ok", async () => {
    const res = await (0, supertest_1.default)(freshApp()).get("/health");
    strict_1.default.equal(res.status, 200);
    strict_1.default.deepEqual(res.body, { status: "ok" });
});
(0, node_test_1.test)("POST /books creates a book and returns 201 with id", async () => {
    const app = freshApp();
    const res = await (0, supertest_1.default)(app)
        .post("/books")
        .send({ title: "Dune", author: "Herbert", year: 1965, isbn: "111" });
    strict_1.default.equal(res.status, 201);
    strict_1.default.equal(res.body.title, "Dune");
    strict_1.default.equal(res.body.author, "Herbert");
    strict_1.default.equal(res.body.year, 1965);
    strict_1.default.equal(res.body.isbn, "111");
    strict_1.default.ok(Number.isInteger(res.body.id));
});
(0, node_test_1.test)("POST /books rejects missing title/author with 400", async () => {
    const app = freshApp();
    const res = await (0, supertest_1.default)(app).post("/books").send({ year: 2000 });
    strict_1.default.equal(res.status, 400);
    strict_1.default.ok(Array.isArray(res.body.errors));
    strict_1.default.equal(res.body.errors.length, 2);
});
(0, node_test_1.test)("GET /books lists all and filters by author", async () => {
    const app = freshApp();
    await (0, supertest_1.default)(app).post("/books").send({ title: "A", author: "Alice" });
    await (0, supertest_1.default)(app).post("/books").send({ title: "B", author: "Bob" });
    await (0, supertest_1.default)(app).post("/books").send({ title: "C", author: "Alice" });
    const all = await (0, supertest_1.default)(app).get("/books");
    strict_1.default.equal(all.status, 200);
    strict_1.default.equal(all.body.length, 3);
    const filtered = await (0, supertest_1.default)(app).get("/books").query({ author: "Alice" });
    strict_1.default.equal(filtered.status, 200);
    strict_1.default.equal(filtered.body.length, 2);
    strict_1.default.ok(filtered.body.every((b) => b.author === "Alice"));
});
(0, node_test_1.test)("GET /books/:id returns one book or 404", async () => {
    const app = freshApp();
    const created = await (0, supertest_1.default)(app)
        .post("/books")
        .send({ title: "Solo", author: "X" });
    const id = created.body.id;
    const found = await (0, supertest_1.default)(app).get(`/books/${id}`);
    strict_1.default.equal(found.status, 200);
    strict_1.default.equal(found.body.title, "Solo");
    const missing = await (0, supertest_1.default)(app).get("/books/99999");
    strict_1.default.equal(missing.status, 404);
    const bad = await (0, supertest_1.default)(app).get("/books/abc");
    strict_1.default.equal(bad.status, 400);
});
(0, node_test_1.test)("PUT /books/:id updates an existing book", async () => {
    const app = freshApp();
    const created = await (0, supertest_1.default)(app)
        .post("/books")
        .send({ title: "Old", author: "Auth", year: 1990 });
    const id = created.body.id;
    const updated = await (0, supertest_1.default)(app)
        .put(`/books/${id}`)
        .send({ title: "New", author: "Auth", year: 2000, isbn: "222" });
    strict_1.default.equal(updated.status, 200);
    strict_1.default.equal(updated.body.title, "New");
    strict_1.default.equal(updated.body.year, 2000);
    strict_1.default.equal(updated.body.isbn, "222");
    const missing = await (0, supertest_1.default)(app)
        .put("/books/99999")
        .send({ title: "Nope", author: "Auth" });
    strict_1.default.equal(missing.status, 404);
    const invalid = await (0, supertest_1.default)(app).put(`/books/${id}`).send({ title: "" });
    strict_1.default.equal(invalid.status, 400);
});
(0, node_test_1.test)("DELETE /books/:id removes a book and 404s after", async () => {
    const app = freshApp();
    const created = await (0, supertest_1.default)(app)
        .post("/books")
        .send({ title: "Temp", author: "Auth" });
    const id = created.body.id;
    const del = await (0, supertest_1.default)(app).delete(`/books/${id}`);
    strict_1.default.equal(del.status, 204);
    const after = await (0, supertest_1.default)(app).get(`/books/${id}`);
    strict_1.default.equal(after.status, 404);
    const delAgain = await (0, supertest_1.default)(app).delete(`/books/${id}`);
    strict_1.default.equal(delAgain.status, 404);
});
