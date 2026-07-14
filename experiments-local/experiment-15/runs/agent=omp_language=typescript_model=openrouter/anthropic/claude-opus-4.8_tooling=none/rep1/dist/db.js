"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BookStore = void 0;
const node_sqlite_1 = require("node:sqlite");
class BookStore {
    db;
    constructor(location = ":memory:") {
        this.db = new node_sqlite_1.DatabaseSync(location);
        this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
    }
    create(input) {
        const stmt = this.db.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)");
        const info = stmt.run(input.title, input.author, input.year ?? null, input.isbn ?? null);
        return this.get(Number(info.lastInsertRowid));
    }
    list(author) {
        if (author !== undefined) {
            return this.db
                .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
                .all(author);
        }
        return this.db
            .prepare("SELECT * FROM books ORDER BY id")
            .all();
    }
    get(id) {
        const row = this.db
            .prepare("SELECT * FROM books WHERE id = ?")
            .get(id);
        return row ?? undefined;
    }
    update(id, input) {
        const existing = this.get(id);
        if (!existing)
            return undefined;
        this.db
            .prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
            .run(input.title, input.author, input.year ?? null, input.isbn ?? null, id);
        return this.get(id);
    }
    delete(id) {
        const info = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
        return info.changes > 0;
    }
    close() {
        this.db.close();
    }
}
exports.BookStore = BookStore;
