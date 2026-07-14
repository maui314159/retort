export interface Book {
  id: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBookInput {
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

export interface UpdateBookInput {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

export function validateBookInput(data: Partial<CreateBookInput>): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!data.title || data.title.trim().length === 0) {
    errors.push({ field: 'title', message: 'Title is required' });
  }

  if (!data.author || data.author.trim().length === 0) {
    errors.push({ field: 'author', message: 'Author is required' });
  }

  if (data.year !== undefined && (typeof data.year !== 'number' || data.year < 0 || data.year > new Date().getFullYear())) {
    errors.push({ field: 'year', message: 'Year must be a valid number between 0 and current year' });
  }

  if (data.isbn !== undefined && data.isbn && !/^(?=(?:\D*\d){10}(?:(?:\D*\d){3})?$)[\d-]+$/.test(data.isbn)) {
    errors.push({ field: 'isbn', message: 'ISBN must be a valid format' });
  }

  return errors;
}
