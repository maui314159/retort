export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface CreateBookRequest {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

export interface UpdateBookRequest {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
}