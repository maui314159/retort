export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateBookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

export interface UpdateBookInput {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
}

export interface ApiError {
  error: string;
}

export type ValidationResult<T> =
  | { valid: true; data: T }
  | { valid: false; error: ApiError };

export type CreateBookValidationResult = ValidationResult<CreateBookInput>;
export type UpdateBookValidationResult = ValidationResult<UpdateBookInput>;
