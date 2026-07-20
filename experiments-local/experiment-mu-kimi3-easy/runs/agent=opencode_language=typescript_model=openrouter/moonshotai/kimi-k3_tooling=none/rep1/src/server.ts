import {
  createServer,
  type IncomingMessage,
  type Server,
  type ServerResponse,
} from "node:http";
import type { DatabaseSync } from "node:sqlite";
import {
  createBook,
  deleteBook,
  getBook,
  listBooks,
  updateBook,
} from "./db.ts";
import { parseBookInput } from "./validation.ts";

const MAX_BODY_BYTES = 1_000_000;

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

function sendNoContent(res: ServerResponse): void {
  res.writeHead(204);
  res.end();
}

function methodNotAllowed(res: ServerResponse, allow: string): void {
  res.setHeader("Allow", allow);
  sendJson(res, 405, { error: "Method not allowed" });
}

/** Read the full request body, rejecting payloads over MAX_BODY_BYTES. */
function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error("Request body too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function parseJsonBody(raw: string): unknown {
  return JSON.parse(raw) as unknown;
}

/** Parse a `/books/:id` id segment into a positive integer, or null if invalid. */
function parseId(segment: string): number | null {
  const id = Number(decodeURIComponent(segment));
  if (!Number.isInteger(id) || id <= 0) {
    return null;
  }
  return id;
}

/** Create the HTTP server for the book API, backed by the given database. */
export function createBookServer(db: DatabaseSync): Server {
  return createServer(async (req, res) => {
    try {
      const method = req.method ?? "GET";
      const url = new URL(req.url ?? "/", "http://localhost");
      const path = url.pathname;

      // GET /health
      if (path === "/health") {
        if (method !== "GET") {
          methodNotAllowed(res, "GET");
          return;
        }
        sendJson(res, 200, { status: "ok" });
        return;
      }

      // /books collection
      if (path === "/books") {
        if (method === "GET") {
          const author = url.searchParams.get("author") ?? undefined;
          sendJson(res, 200, listBooks(db, author));
          return;
        }
        if (method === "POST") {
          let data: unknown;
          try {
            data = parseJsonBody(await readBody(req));
          } catch {
            sendJson(res, 400, { error: "Request body must be valid JSON" });
            return;
          }
          const parsed = parseBookInput(data);
          if (!parsed.ok) {
            sendJson(res, 400, { error: parsed.error });
            return;
          }
          sendJson(res, 201, createBook(db, parsed.value));
          return;
        }
        methodNotAllowed(res, "GET, POST");
        return;
      }

      // /books/:id
      const itemMatch = /^\/books\/([^/]+)$/.exec(path);
      if (itemMatch !== null) {
        const id = parseId(itemMatch[1] ?? "");
        if (id === null) {
          sendJson(res, 400, { error: "Invalid book id" });
          return;
        }

        if (method === "GET") {
          const book = getBook(db, id);
          if (book === null) {
            sendJson(res, 404, { error: "Book not found" });
            return;
          }
          sendJson(res, 200, book);
          return;
        }

        if (method === "PUT") {
          let data: unknown;
          try {
            data = parseJsonBody(await readBody(req));
          } catch {
            sendJson(res, 400, { error: "Request body must be valid JSON" });
            return;
          }
          const parsed = parseBookInput(data);
          if (!parsed.ok) {
            sendJson(res, 400, { error: parsed.error });
            return;
          }
          const book = updateBook(db, id, parsed.value);
          if (book === null) {
            sendJson(res, 404, { error: "Book not found" });
            return;
          }
          sendJson(res, 200, book);
          return;
        }

        if (method === "DELETE") {
          if (!deleteBook(db, id)) {
            sendJson(res, 404, { error: "Book not found" });
            return;
          }
          sendNoContent(res);
          return;
        }

        methodNotAllowed(res, "GET, PUT, DELETE");
        return;
      }

      sendJson(res, 404, { error: "Not found" });
    } catch (err) {
      console.error("Unhandled error:", err);
      sendJson(res, 500, { error: "Internal server error" });
    }
  });
}
