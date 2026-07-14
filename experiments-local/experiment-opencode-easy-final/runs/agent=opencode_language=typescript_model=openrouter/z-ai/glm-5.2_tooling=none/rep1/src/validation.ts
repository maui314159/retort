import type { CreateBookInput, UpdateBookInput } from "./types";

export class ValidationError extends Error {
  public readonly statusCode = 400;
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

export function validateCreate(input: unknown): CreateBookInput {
  if (typeof input !== "object" || input === null) {
    throw new ValidationError("Request body must be a JSON object");
  }
  const body = input as Record<string, unknown>;

  const title = body.title;
  if (typeof title !== "string" || title.trim() === "") {
    throw new ValidationError("'title' is required and must be a non-empty string");
  }

  const author = body.author;
  if (typeof author !== "string" || author.trim() === "") {
    throw new ValidationError("'author' is required and must be a non-empty string");
  }

  const year = body.year;
  if (year !== undefined && year !== null) {
    if (typeof year !== "number" || !Number.isInteger(year)) {
      throw new ValidationError("'year' must be an integer or null");
    }
    if (year < 0 || year > new Date().getFullYear() + 5) {
      throw new ValidationError("'year' is out of range");
    }
  }

  const isbn = body.isbn;
  if (isbn !== undefined && isbn !== null) {
    if (typeof isbn !== "string") {
      throw new ValidationError("'isbn' must be a string or null");
    }
  }

  return {
    title: title.trim(),
    author: author.trim(),
    year: typeof year === "number" ? year : null,
    isbn: typeof isbn === "string" ? isbn.trim() : null,
  };
}

export function validateUpdate(input: unknown): UpdateBookInput {
  if (typeof input !== "object" || input === null) {
    throw new ValidationError("Request body must be a JSON object");
  }
  const body = input as Record<string, unknown>;
  const result: UpdateBookInput = {};

  if (body.title !== undefined) {
    if (typeof body.title !== "string" || body.title.trim() === "") {
      throw new ValidationError("'title' must be a non-empty string");
    }
    result.title = body.title.trim();
  }

  if (body.author !== undefined) {
    if (typeof body.author !== "string" || body.author.trim() === "") {
      throw new ValidationError("'author' must be a non-empty string");
    }
    result.author = body.author.trim();
  }

  if (body.year !== undefined) {
    if (body.year === null) {
      result.year = null;
    } else if (typeof body.year !== "number" || !Number.isInteger(body.year)) {
      throw new ValidationError("'year' must be an integer or null");
    } else if (body.year < 0 || body.year > new Date().getFullYear() + 5) {
      throw new ValidationError("'year' is out of range");
    } else {
      result.year = body.year;
    }
  }

  if (body.isbn !== undefined) {
    if (body.isbn === null) {
      result.isbn = null;
    } else if (typeof body.isbn !== "string") {
      throw new ValidationError("'isbn' must be a string or null");
    } else {
      result.isbn = body.isbn.trim();
    }
  }

  return result;
}
