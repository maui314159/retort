import { z } from "zod";

export const bookCreateSchema = z.object({
  title: z
    .string({
      required_error: "title is required",
      invalid_type_error: "title is required",
    })
    .trim()
    .min(1, "title is required"),
  author: z
    .string({
      required_error: "author is required",
      invalid_type_error: "author is required",
    })
    .trim()
    .min(1, "author is required"),
  year: z
    .number()
    .int()
    .min(0, "year must be a non-negative integer")
    .max(2100, "year must be a realistic value")
    .nullish()
    .or(z.literal("")),
  isbn: z.string().trim().nullish().or(z.literal("")),
});

export const bookUpdateSchema = bookCreateSchema.partial();

export type BookCreate = z.infer<typeof bookCreateSchema>;
export type BookUpdate = z.infer<typeof bookUpdateSchema>;

export function normalizeCreate(input: BookCreate): {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
} {
  return {
    title: input.title,
    author: input.author,
    year:
      input.year === undefined || input.year === null || input.year === ""
        ? null
        : Number(input.year),
    isbn:
      input.isbn === undefined || input.isbn === null || input.isbn === ""
        ? null
        : input.isbn,
  };
}

export function normalizeUpdate(input: BookUpdate): {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
} {
  const out: {
    title?: string;
    author?: string;
    year?: number | null;
    isbn?: string | null;
  } = {};
  if (input.title !== undefined) out.title = input.title;
  if (input.author !== undefined) out.author = input.author;
  if (input.year !== undefined) {
    out.year =
      input.year === null || input.year === "" ? null : Number(input.year);
  }
  if (input.isbn !== undefined) {
    out.isbn = input.isbn === null || input.isbn === "" ? null : input.isbn;
  }
  return out;
}
