export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookUpdate {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
}

export class ValidationError extends Error {
  public readonly details: string[];
  constructor(details: string[]) {
    super(`Validation failed: ${details.join("; ")}`);
    this.name = "ValidationError";
    this.details = details;
  }
}

const ISBN_PATTERN = /^[0-9Xx\- ]{10,17}$/;

function asString(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (value == null) return null;
  return null;
}

function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.trunc(value);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") return null;
    const n = Number(trimmed);
    if (Number.isFinite(n)) return Math.trunc(n);
  }
  return NaN;
}

function normalizeIsbn(raw: string | null): string | null {
  if (raw === null) return null;
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  return trimmed;
}

function ensureObject(raw: unknown): Record<string, unknown> {
  if (typeof raw !== "object" || raw === null) {
    throw new ValidationError(["request body must be a JSON object"]);
  }
  return raw as Record<string, unknown>;
}

function requireNonEmptyString(
  body: Record<string, unknown>,
  field: string,
  errors: string[]
): string | null {
  const value = asString(body[field]);
  if (value === null) {
    errors.push(`${field} is required and must be a string`);
    return null;
  }
  const trimmed = value.trim();
  if (trimmed === "") {
    errors.push(`${field} is required and must be a string`);
    return null;
  }
  return trimmed;
}

function optionalYear(
  body: Record<string, unknown>,
  errors: string[]
): number | null | undefined {
  if (!("year" in body)) return undefined;
  const n = asNumber(body.year);
  if (n === null) return null;
  if (Number.isNaN(n)) {
    errors.push("year must be a number");
    return undefined;
  }
  if (n < 0 || n > 9999) {
    errors.push("year must be between 0 and 9999");
    return undefined;
  }
  return n;
}

function optionalIsbn(
  body: Record<string, unknown>,
  errors: string[]
): string | null | undefined {
  if (!("isbn" in body)) return undefined;
  if (body.isbn === null) return null;
  const s = asString(body.isbn);
  if (s === null) {
    errors.push("isbn must be a string or null");
    return undefined;
  }
  const normalized = normalizeIsbn(s);
  if (normalized !== null && !ISBN_PATTERN.test(normalized)) {
    errors.push("isbn has an invalid format");
    return undefined;
  }
  return normalized;
}

export function parseCreateBook(raw: unknown): BookInput {
  const body = ensureObject(raw);
  const errors: string[] = [];
  const title = requireNonEmptyString(body, "title", errors);
  const author = requireNonEmptyString(body, "author", errors);
  const year = optionalYear(body, errors);
  const isbn = optionalIsbn(body, errors);
  if (errors.length > 0) throw new ValidationError(errors);
  return {
    title: title as string,
    author: author as string,
    year: year as number | null,
    isbn: isbn as string | null,
  };
}

export function parseUpdateBook(raw: unknown): BookUpdate {
  const body = ensureObject(raw);
  const errors: string[] = [];
  const update: BookUpdate = {};
  if ("title" in body) {
    const t = requireNonEmptyString(body, "title", errors);
    if (t !== null) update.title = t;
  }
  if ("author" in body) {
    const a = requireNonEmptyString(body, "author", errors);
    if (a !== null) update.author = a;
  }
  if ("year" in body) {
    const y = optionalYear(body, errors);
    if (y !== undefined) update.year = y;
  }
  if ("isbn" in body) {
    const i = optionalIsbn(body, errors);
    if (i !== undefined) update.isbn = i;
  }
  if (Object.keys(update).length === 0) {
    errors.push("at least one of title, author, year, isbn must be provided");
  }
  if (errors.length > 0) throw new ValidationError(errors);
  return update;
}
