import type { BookInput } from './db.js';

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: string[] };

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

function isOptionalString(v: unknown): v is string | null | undefined {
  return v === undefined || v === null || typeof v === 'string';
}

function isOptionalNumber(v: unknown): v is number | null | undefined {
  if (v === undefined || v === null) return true;
  return typeof v === 'number' && Number.isFinite(v);
}

export function parseBookInput(raw: unknown): ValidationResult {
  if (raw === null || typeof raw !== 'object') {
    return { ok: false, errors: ['request body must be a JSON object'] };
  }
  const body = raw as Record<string, unknown>;

  const errors: string[] = [];

  if (!isNonEmptyString(body.title)) {
    errors.push('title is required and must be a non-empty string');
  }
  if (!isNonEmptyString(body.author)) {
    errors.push('author is required and must be a non-empty string');
  }
  if (!isOptionalString(body.isbn)) {
    errors.push('isbn must be a string when provided');
  }
  if (!isOptionalNumber(body.year)) {
    errors.push('year must be a number when provided');
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  const value: BookInput = {
    title: (body.title as string).trim(),
    author: (body.author as string).trim(),
    year: body.year === undefined || body.year === null ? null : (body.year as number),
    isbn:
      body.isbn === undefined || body.isbn === null
        ? null
        : ((body.isbn as string).trim() || null),
  };
  return { ok: true, value };
}

export function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  if (!Number.isSafeInteger(n) || n <= 0) return null;
  return n;
}
