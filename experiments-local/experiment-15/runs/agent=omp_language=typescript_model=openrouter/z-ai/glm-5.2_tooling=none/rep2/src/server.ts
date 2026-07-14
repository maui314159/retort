import type { BookStore } from "./db.ts";
import { validateBook } from "./validation.ts";
import type { BookInput } from "./types.ts";

export interface ServerOptions {
  port: number;
  store: BookStore;
}

export function createServer({ port, store }: ServerOptions) {
  const server = Bun.serve({
    port,
    fetch(req) {
      return handleRequest(req, store);
    },
  });
  return server;
}

async function handleRequest(req: Request, store: BookStore): Promise<Response> {
  const url = new URL(req.url);
  const { pathname } = url;
  const method = req.method;

  // Health check
  if (method === "GET" && pathname === "/health") {
    return json({ status: "ok" });
  }

  // Books collection
  if (pathname === "/books") {
    if (method === "GET") {
      const author = url.searchParams.get("author");
      const books = store.list(author ?? undefined);
      return json(books);
    }
    if (method === "POST") {
      return await createBook(req, store);
    }
    return methodNotAllowed(["GET", "POST"]);
  }

  // Single book
  const match = pathname.match(/^\/books\/(\d+)$/);
  if (match) {
    const id = Number(match[1]);
    if (method === "GET") {
      const book = store.get(id);
      return book ? json(book) : notFound(`Book ${id} not found`);
    }
    if (method === "PUT") {
      return await updateBook(req, store, id);
    }
    if (method === "DELETE") {
      const deleted = store.delete(id);
      return deleted ? json({ id, deleted: true }) : notFound(`Book ${id} not found`);
    }
    return methodNotAllowed(["GET", "PUT", "DELETE"]);
  }

  return notFound(`Route ${method} ${pathname} not found`);
}

async function createBook(req: Request, store: BookStore): Promise<Response> {
  const parsed = await parseBody(req);
  if (!parsed.ok) return parsed.response;
  const errors = validateBook(parsed.value, false);
  if (errors.length > 0) return validationError(errors);
  const book = store.create(parsed.value);
  return json(book, 201);
}

async function updateBook(req: Request, store: BookStore, id: number): Promise<Response> {
  const parsed = await parseBody(req);
  if (!parsed.ok) return parsed.response;
  const errors = validateBook(parsed.value, true);
  if (errors.length > 0) return validationError(errors);
  const book = store.update(id, parsed.value);
  return book ? json(book) : notFound(`Book ${id} not found`);
}

type ParseResult =
  | { ok: true; value: BookInput }
  | { ok: false; response: Response };

async function parseBody(req: Request): Promise<ParseResult> {
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    return { ok: false, response: json({ error: "Invalid JSON body" }, 400) };
  }
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
    return { ok: false, response: json({ error: "Request body must be a JSON object" }, 400) };
  }
  const obj = raw as Record<string, unknown>;
  return {
    ok: true,
    value: {
      title: obj.title,
      author: obj.author,
      year: obj.year,
      isbn: obj.isbn,
    },
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function notFound(message: string): Response {
  return json({ error: message }, 404);
}

function methodNotAllowed(allowed: string[]): Response {
  return new Response(JSON.stringify({ error: "Method not allowed" }), {
    status: 405,
    headers: {
      "Content-Type": "application/json",
      Allow: allowed.join(", "),
    },
  });
}

function validationError(errors: { field: string; message: string }[]): Response {
  return json({ error: "Validation failed", errors }, 422);
}
