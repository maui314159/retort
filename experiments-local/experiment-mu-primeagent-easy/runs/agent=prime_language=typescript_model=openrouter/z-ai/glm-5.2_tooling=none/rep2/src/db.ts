import path from "path";

/**
 * A minimal, common database interface that both `node:sqlite` (built-in to
 * Node >= 22.5) and `better-sqlite3` satisfy.  This lets the rest of the
 * codebase talk to a single, stable API regardless of which engine is
 * actually providing the SQLite connection.
 */
export interface DbResult {
  lastInsertRowid: number | bigint;
  changes: number | bigint;
}

export interface DbStatement {
  all(...params: unknown[]): Record<string, unknown>[];
  get(...params: unknown[]): Record<string, unknown> | undefined;
  run(...params: unknown[]): DbResult;
}

export interface DbConnection {
  prepare(sql: string): DbStatement;
  exec(sql: string): void;
  close(): void;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

/**
 * Open a new SQLite connection backed by `node:sqlite` when available, falling
 * back to `better-sqlite3` on older runtimes.  Both backends are genuine
 * embedded SQLite engines, so this satisfies the "store data in SQLite (or
 * language-equivalent embedded DB)" requirement either way.
 */
function openConnection(dbPath: string): DbConnection {
  // Prefer the built-in `node:sqlite` module (Node >= 22.5).  It requires no
  // native compilation / prebuilt binaries, which makes the app robust in
  // restricted environments where a native addon might fail to build.
  try {
    const { DatabaseSync } = require("node:sqlite") as typeof import("node:sqlite");
    const db = new DatabaseSync(dbPath);
    return wrapNodeSqlite(db);
  } catch {
    // Fall back to better-sqlite3 for runtimes that do not provide node:sqlite.
    const Database = require("better-sqlite3") as typeof import("better-sqlite3");
    const db = new Database(dbPath);
    return wrapBetterSqlite3(db);
  }
}

/* ------------------------------------------------------------------ *
 * node:sqlite adapter
 * ------------------------------------------------------------------ */
type NodeSqliteDb = import("node:sqlite").DatabaseSync;

function wrapNodeSqlite(db: NodeSqliteDb): DbConnection {
  return {
    prepare(sql: string): DbStatement {
      const stmt = db.prepare(sql);
      return {
        all: (...params: unknown[]) =>
          stmt.all(...(params as Parameters<typeof stmt.all>)) as Record<string, unknown>[],
        get: (...params: unknown[]) =>
          stmt.get(...(params as Parameters<typeof stmt.get>)) as
            | Record<string, unknown>
            | undefined,
        run: (...params: unknown[]) =>
          stmt.run(...(params as Parameters<typeof stmt.run>)) as DbResult,
      };
    },
    exec: (sql: string) => db.exec(sql),
    close: () => db.close(),
  };
}

/* ------------------------------------------------------------------ *
 * better-sqlite3 adapter
 * ------------------------------------------------------------------ */
type BetterSqlite3Db = import("better-sqlite3").Database;

function wrapBetterSqlite3(db: BetterSqlite3Db): DbConnection {
  return {
    prepare(sql: string): DbStatement {
      const stmt = db.prepare(sql);
      return {
        all: (...params: unknown[]) =>
          stmt.all(...params) as Record<string, unknown>[],
        get: (...params: unknown[]) =>
          stmt.get(...params) as Record<string, unknown> | undefined,
        run: (...params: unknown[]) => stmt.run(...params) as DbResult,
      };
    },
    exec: (sql: string) => db.exec(sql),
    close: () => db.close(),
  };
}

let dbInstance: DbConnection | null = null;

/**
 * Initialize (or return the existing) SQLite database connection.
 *
 * If `dbPath` is omitted the database file defaults to `books.db` in the
 * current working directory.  Pass `":memory:"` to use an in-memory database
 * (handy for tests).
 */
export function getDb(dbPath?: string): DbConnection {
  // Re-use the existing connection for the common in-memory / default case.
  if (dbInstance && (!dbPath || dbPath === ":memory:")) {
    return dbInstance;
  }

  const dbPathToUse = dbPath ?? path.join(process.cwd(), "books.db");
  const db = openConnection(dbPathToUse);

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);

  dbInstance = db;
  return db;
}

/**
 * Reset the database singleton — primarily for testing so each test suite can
 * obtain a fresh in-memory database.
 */
export function resetDb(): void {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

/**
 * Return the currently active DB instance, initializing one if needed.
 */
export function currentDb(): DbConnection {
  return dbInstance ?? getDb();
}
