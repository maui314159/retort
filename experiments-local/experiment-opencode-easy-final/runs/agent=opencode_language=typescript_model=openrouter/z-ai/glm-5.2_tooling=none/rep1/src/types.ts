export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
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
