/**
 * Domain types for the book collection API.
 */

/** A book record as stored in the database. */
export interface Book {
  id: number;
  title: string;
  author: string;
  /** Publication year, or null when unknown. */
  year: number | null;
  /** ISBN identifier, or null when unknown. */
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

/** Raw payload accepted by POST /books and PUT /books/{id} (untrusted). */
export interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

/** Normalised, validated book payload. */
export interface ValidatedBookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/** Standard error response body. */
export interface ErrorResponse {
  error: string;
  details?: Record<string, string>;
}
