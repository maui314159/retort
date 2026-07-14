export interface BookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

export interface BookRecord {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookUpdateInput {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
}

export interface ApiError {
  error: string;
  details?: unknown;
}
