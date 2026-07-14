import { z } from "zod";

export const bookSchema = z.object({
  title: z.string().min(1, "title is required"),
  author: z.string().min(1, "author is required"),
  year: z.number().int().nullable().optional(),
  isbn: z.string().nullable().optional(),
});

export type BookInput = z.infer<typeof bookSchema>;

export function validateBook(input: unknown):
  | { ok: true; value: BookInput }
  | { ok: false; errors: string[] } {
  const result = bookSchema.safeParse(input);
  if (result.success) {
    return { ok: true, value: result.data };
  }
  const errors = result.error.issues.map(
    (i) => `${i.path.join(".")}: ${i.message}`,
  );
  return { ok: false, errors };
}
