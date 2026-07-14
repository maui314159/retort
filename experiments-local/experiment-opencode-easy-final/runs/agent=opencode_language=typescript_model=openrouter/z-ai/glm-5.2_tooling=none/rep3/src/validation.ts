import { z } from "zod";

export const createBookSchema = z.object({
  title: z.string().min(1, "title is required").max(500),
  author: z.string().min(1, "author is required").max(500),
  year: z.number().int().min(0).max(9999).optional().nullable(),
  isbn: z.string().max(100).optional().nullable(),
});

export const updateBookSchema = z.object({
  title: z.string().min(1, "title is required").max(500).optional(),
  author: z.string().min(1, "author is required").max(500).optional(),
  year: z.number().int().min(0).max(9999).optional().nullable(),
  isbn: z.string().max(100).optional().nullable(),
});

export type CreateBookInput = z.infer<typeof createBookSchema>;
export type UpdateBookInput = z.infer<typeof updateBookSchema>;

export function formatZodError(err: z.ZodError): { message: string; details: unknown } {
  return {
    message: "Validation failed",
    details: err.issues.map((i) => ({
      path: i.path.join("."),
      message: i.message,
      code: i.code,
    })),
  };
}
