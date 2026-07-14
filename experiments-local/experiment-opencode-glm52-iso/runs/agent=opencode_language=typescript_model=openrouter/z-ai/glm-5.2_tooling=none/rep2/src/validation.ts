import type { Request, Response, NextFunction } from "express";
import type { NewBook } from "./db";

export type ValidationResult =
  | { ok: true; value: NewBook }
  | { ok: false; errors: string[] };

export function validateBook(input: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof input !== "object" || input === null) {
    return { ok: false, errors: ["Body must be a JSON object"] };
  }

  const body = input as Record<string, unknown>;

  if (typeof body.title !== "string" || body.title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }

  if (typeof body.author !== "string" || body.author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }

  if (
    body.year !== undefined &&
    body.year !== null &&
    (typeof body.year !== "number" || !Number.isInteger(body.year))
  ) {
    errors.push("year must be an integer or null");
  }

  if (
    body.isbn !== undefined &&
    body.isbn !== null &&
    typeof body.isbn !== "string"
  ) {
    errors.push("isbn must be a string or null");
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    value: {
      title: (body.title as string).trim(),
      author: (body.author as string).trim(),
      year:
        body.year === undefined || body.year === null
          ? null
          : (body.year as number),
      isbn:
        body.isbn === undefined || body.isbn === null
          ? null
          : (body.isbn as string),
    },
  };
}

export function validationMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const result = validateBook(req.body);
  if (!result.ok) {
    res.status(400).json({ errors: result.errors });
    return;
  }
  res.locals.newBook = result.value;
  next();
}
