import { z } from "zod";

const trimmedNonEmpty = z
  .string({ required_error: "title is required" })
  .transform((s) => s.trim())
  .refine((s) => s.length > 0, { message: "title must not be empty" });

const yearSchema = z
  .number()
  .int()
  .gte(-3000, "year is out of range")
  .lte(9999, "year is out of range")
  .nullish()
  .transform((v) => v ?? undefined);

const isbnSchema = z
  .string()
  .trim()
  .max(32, "isbn is too long")
  .nullish()
  .transform((v) => (v == null || v.length > 0 ? v : null));

export const bookCreateSchema = z
  .object({
    title: trimmedNonEmpty,
    author: trimmedNonEmpty,
    year: yearSchema,
    isbn: isbnSchema,
  })
  .strict();

export const bookUpdateSchema = z
  .object({
    title: trimmedNonEmpty.optional(),
    author: trimmedNonEmpty.optional(),
    year: yearSchema,
    isbn: isbnSchema,
  })
  .strict()
  .refine(
    (v) =>
      v.title !== undefined ||
      v.author !== undefined ||
      v.year !== undefined ||
      v.isbn !== undefined,
    { message: "at least one field must be provided" },
  );

export type BookCreateInput = z.infer<typeof bookCreateSchema>;
export type BookUpdateInput = z.infer<typeof bookUpdateSchema>;
