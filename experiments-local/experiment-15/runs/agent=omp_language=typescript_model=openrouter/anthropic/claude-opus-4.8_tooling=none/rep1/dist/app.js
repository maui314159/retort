"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createApp = createApp;
const express_1 = __importDefault(require("express"));
function validateBook(body) {
    const errors = [];
    if (typeof body !== "object" || body === null) {
        return { ok: false, errors: ["request body must be a JSON object"] };
    }
    const b = body;
    if (typeof b.title !== "string" || b.title.trim() === "") {
        errors.push("title is required and must be a non-empty string");
    }
    if (typeof b.author !== "string" || b.author.trim() === "") {
        errors.push("author is required and must be a non-empty string");
    }
    let year = null;
    if (b.year !== undefined && b.year !== null) {
        if (typeof b.year !== "number" || !Number.isInteger(b.year)) {
            errors.push("year must be an integer");
        }
        else {
            year = b.year;
        }
    }
    let isbn = null;
    if (b.isbn !== undefined && b.isbn !== null) {
        if (typeof b.isbn !== "string") {
            errors.push("isbn must be a string");
        }
        else {
            isbn = b.isbn;
        }
    }
    if (errors.length > 0)
        return { ok: false, errors };
    return {
        ok: true,
        errors,
        value: {
            title: b.title.trim(),
            author: b.author.trim(),
            year,
            isbn,
        },
    };
}
function parseId(raw) {
    if (!/^\d+$/.test(raw))
        return null;
    const id = Number(raw);
    return Number.isSafeInteger(id) ? id : null;
}
function createApp(store) {
    const app = (0, express_1.default)();
    app.use(express_1.default.json());
    app.get("/health", (_req, res) => {
        res.status(200).json({ status: "ok" });
    });
    app.post("/books", (req, res) => {
        const result = validateBook(req.body);
        if (!result.ok) {
            return res.status(400).json({ errors: result.errors });
        }
        const book = store.create(result.value);
        res.status(201).json(book);
    });
    app.get("/books", (req, res) => {
        const author = req.query.author;
        if (author !== undefined && typeof author !== "string") {
            return res.status(400).json({ errors: ["author filter must be a single string"] });
        }
        res.status(200).json(store.list(author));
    });
    app.get("/books/:id", (req, res) => {
        const id = parseId(req.params.id);
        if (id === null) {
            return res.status(400).json({ errors: ["id must be a positive integer"] });
        }
        const book = store.get(id);
        if (!book)
            return res.status(404).json({ errors: ["book not found"] });
        res.status(200).json(book);
    });
    app.put("/books/:id", (req, res) => {
        const id = parseId(req.params.id);
        if (id === null) {
            return res.status(400).json({ errors: ["id must be a positive integer"] });
        }
        const result = validateBook(req.body);
        if (!result.ok) {
            return res.status(400).json({ errors: result.errors });
        }
        const book = store.update(id, result.value);
        if (!book)
            return res.status(404).json({ errors: ["book not found"] });
        res.status(200).json(book);
    });
    app.delete("/books/:id", (req, res) => {
        const id = parseId(req.params.id);
        if (id === null) {
            return res.status(400).json({ errors: ["id must be a positive integer"] });
        }
        const deleted = store.delete(id);
        if (!deleted)
            return res.status(404).json({ errors: ["book not found"] });
        res.status(204).send();
    });
    // JSON parse error handler
    app.use((err, _req, res, next) => {
        if (err && err.name === "SyntaxError") {
            return res.status(400).json({ errors: ["invalid JSON body"] });
        }
        next(err);
    });
    return app;
}
