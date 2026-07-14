use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

use crate::error::ApiError;

/// A book resource as stored and returned by the API.
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl Book {
    /// Build a new `Book` from validated input, assigning a fresh UUID.
    pub fn new(input: BookInput) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            title: input.title,
            author: input.author,
            year: input.year,
            isbn: input.isbn,
        }
    }
}

/// Payload accepted by `POST /books` and `PUT /books/{id}`.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Enforce the validation rules: `title` and `author` must be non-empty.
    pub fn validate(&self) -> Result<(), ApiError> {
        if self.title.trim().is_empty() {
            return Err(ApiError::BadRequest("title is required".into()));
        }
        if self.author.trim().is_empty() {
            return Err(ApiError::BadRequest("author is required".into()));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn input(title: &str, author: &str) -> BookInput {
        BookInput {
            title: title.to_string(),
            author: author.to_string(),
            year: None,
            isbn: None,
        }
    }

    #[test]
    fn validate_accepts_non_empty_fields() {
        assert!(input("1984", "George Orwell").validate().is_ok());
    }

    #[test]
    fn validate_rejects_empty_title() {
        let err = input("", "George Orwell").validate().unwrap_err();
        matches!(err, ApiError::BadRequest(_));
    }

    #[test]
    fn validate_rejects_whitespace_only_title() {
        let err = input("   ", "George Orwell").validate().unwrap_err();
        matches!(err, ApiError::BadRequest(_));
    }

    #[test]
    fn validate_rejects_empty_author() {
        let err = input("1984", "").validate().unwrap_err();
        matches!(err, ApiError::BadRequest(_));
    }

    #[test]
    fn new_assigns_unique_ids() {
        let a = Book::new(input("A", "X"));
        let b = Book::new(input("A", "X"));
        assert_ne!(a.id, b.id);
        assert!(!a.id.is_empty());
    }
}
