import { z } from "zod";

export const bookCreateSchema = z.object({
  title: z.string().min(1, "title is required"),
  author: z.string().min(1, "author is required"),
  year: z
    .number()
    .int()
    .min(0)
    .max(9999)
    .optional()
    .nullable()
    .or(z.undefined()),
  isbn: z.string().optional().nullable().or(z.undefined()),
});

export const bookUpdateSchema = z
  .object({
    title: z.string().min(1).optional(),
    author: z.string().min(1).optional(),
    year: z.number().int().min(0).max(9999).optional().nullable(),
    isbn: z.string().optional().nullable(),
  })
  .refine((data) => Object.keys(data).length > 0, {
    message: "at least one field must be provided to update",
  });

export function parseCreate(input: unknown) {
  return bookCreateSchema.parse(input);
}

export function parseUpdate(input: unknown) {
  return bookUpdateSchema.parse(input);
}

export function formatZodError(err: z.ZodError): { error: string; details: unknown } {
  return {
    error: "validation_failed",
    details: err.issues.map((i) => ({ path: i.path.join("."), message: i.message })),
  };
}
