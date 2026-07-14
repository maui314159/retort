//! Domain models for the books API.
//!
//! `Book` is the canonical stored representation. `NewBook` is the input
//! shape accepted on `POST`; `BookUpdate` is the input shape for `PUT`.

use serde::{Deserialize, Serialize};

use crate::error::AppError;

/// A book as stored in the database.
#[derive(Debug, Clone, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Input for creating a book. Title and author are required and must be
/// non-empty after trimming.
#[derive(Debug, Deserialize)]
pub struct NewBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl NewBook {
    /// Validate and normalize the input, returning a [`Book`] ready to be
    /// persisted (without an id).
    pub fn validate(self) -> Result<ValidatedNewBook, AppError> {
        let title = require_non_empty(self.title, "title")?;
        let author = require_non_empty(self.author, "author")?;

        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                return Err(AppError::Validation(format!(
                    "year must be between 0 and 9999 (got {year})"
                )));
            }
        }

        Ok(ValidatedNewBook {
            title,
            author,
            year: self.year,
            isbn: self
                .isbn
                .and_then(|s| non_empty(s).map(|s| s.to_string())),
        })
    }
}

/// A `NewBook` that has passed validation. The title and author are now
/// non-empty strings; `isbn` is normalized to `None` if blank.
#[derive(Debug)]
pub struct ValidatedNewBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Input for updating a book. Title and author are required and must be
/// non-empty after trimming. Year and isbn are optional; `null` clears
/// the field on the stored record.
#[derive(Debug, Deserialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookUpdate {
    /// Validate and normalize the input, returning a [`ValidatedBookUpdate`]
    /// suitable for partial replacement via `PUT`.
    pub fn validate(self) -> Result<ValidatedBookUpdate, AppError> {
        let title = require_non_empty(self.title, "title")?;
        let author = require_non_empty(self.author, "author")?;

        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                return Err(AppError::Validation(format!(
                    "year must be between 0 and 9999 (got {year})"
                )));
            }
        }

        // `Option<Option<String>>` is awkward in serde; the update contract
        // treats a present-but-empty isbn as "clear the field" by mapping it
        // to None, and an absent field as "leave as-is" is intentionally not
        let isbn = self
            .isbn
            .and_then(|s| non_empty(s).map(|s| s.to_string()));

        Ok(ValidatedBookUpdate {
            title,
            author,
            year: self.year,
            isbn,
        })
    }
}

/// A `BookUpdate` that has passed validation.
#[derive(Debug)]
pub struct ValidatedBookUpdate {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

fn require_non_empty(field: Option<String>, name: &str) -> Result<String, AppError> {
    match field.and_then(non_empty) {
        Some(value) => Ok(value.to_string()),
        None => Err(AppError::Validation(format!(
            "{name} is required and must be non-empty"
        ))),
    }
}

fn non_empty(s: String) -> Option<String> {
    let trimmed = s.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_book_requires_title_and_author() {
        let err = NewBook {
            title: None,
            author: Some("An Author".to_string()),
            year: None,
            isbn: None,
        }
        .validate()
        .unwrap_err();
        assert!(matches!(err, AppError::Validation(ref m) if m.contains("title")));

        let err = NewBook {
            title: Some("A Title".to_string()),
            author: None,
            year: None,
            isbn: None,
        }
        .validate()
        .unwrap_err();
        assert!(matches!(err, AppError::Validation(ref m) if m.contains("author")));

        let err = NewBook {
            title: Some("   ".to_string()),
            author: Some("X".to_string()),
            year: None,
            isbn: None,
        }
        .validate()
        .unwrap_err();
        assert!(matches!(err, AppError::Validation(ref m) if m.contains("title")));
    }

    #[test]
    fn new_book_trims_and_drops_blank_isbn() {
        let v = NewBook {
            title: Some("  Title  ".to_string()),
            author: Some("  Author  ".to_string()),
            year: Some(2020),
            isbn: Some("   ".to_string()),
        }
        .validate()
        .expect("valid");
        assert_eq!(v.title, "Title");
        assert_eq!(v.author, "Author");
        assert_eq!(v.year, Some(2020));
        assert_eq!(v.isbn, None);
    }

    #[test]
    fn new_book_rejects_out_of_range_year() {
        let err = NewBook {
            title: Some("T".to_string()),
            author: Some("A".to_string()),
            year: Some(10_000),
            isbn: None,
        }
        .validate()
        .unwrap_err();
        assert!(matches!(err, AppError::Validation(ref m) if m.contains("year")));
    }

    #[test]
    fn book_update_requires_title_and_author() {
        let err = BookUpdate {
            title: None,
            author: Some("A".to_string()),
            year: None,
            isbn: None,
        }
        .validate()
        .unwrap_err();
        assert!(matches!(err, AppError::Validation(ref m) if m.contains("title")));
    }
}
