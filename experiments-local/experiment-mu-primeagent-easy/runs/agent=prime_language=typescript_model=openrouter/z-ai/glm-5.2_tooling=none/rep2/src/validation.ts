import { z } from "zod";

/**
 * Validation schema for creating / updating a book.
 * - title: required, non-empty string
 * - author: required, non-empty string
 * - year: optional integer (>= 0)
 * - isbn: optional string
 */
export const bookSchema = z.object({
  title: z.string().min(1, "title is required and must be non-empty"),
  author: z.string().min(1, "author is required and must be non-empty"),
  year: z
    .number()
    .int("year must be an integer")
    .min(0, "year must be a positive number")
    .optional(),
  isbn: z.string().optional(),
});

export type BookSchema = z.infer<typeof bookSchema>;

/**
 * Partial schema for updates — all fields optional, but if present
 * they must still satisfy the same constraints.
 */
export const bookUpdateSchema = bookSchema.partial();

export type BookUpdateSchema = z.infer<typeof bookUpdateSchema>;
