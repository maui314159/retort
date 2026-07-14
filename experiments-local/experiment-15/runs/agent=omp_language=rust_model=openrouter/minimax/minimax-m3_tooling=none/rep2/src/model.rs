//! Book domain model and validation.
//!
//! Public types are the API contract:
//! - [`Book`] is the stored representation returned to clients.
//! - [`BookCreate`] is the body of `POST /books`.
//! - [`BookUpdate`] is the body of `PUT /books/{id}`.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::error::{AppError, AppResult};

/// Maximum length for free-text fields. Generous but bounded.
pub const MAX_TITLE_LEN: usize = 500;
pub const MAX_AUTHOR_LEN: usize = 200;
pub const MAX_ISBN_LEN: usize = 32;

/// A book as stored in the database and returned by the API.
#[derive(Debug, Clone, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    /// Publication year; `None` if unknown.
    pub year: Option<i32>,
    /// International Standard Book Number; `None` if not provided.
    pub isbn: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Payload for `POST /books`.
#[derive(Debug, Clone, Deserialize)]
pub struct BookCreate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Payload for `PUT /books/{id}`.
///
/// All fields except `id` are required for a full update; partial updates
/// would belong on `PATCH`. The route uses [`BookUpdate::validate`] to
/// enforce non-empty `title` / `author` before persisting.
#[derive(Debug, Clone, Deserialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookCreate {
    /// Validate the incoming payload and return a trimmed [`ValidatedBookCreate`]
    /// ready for persistence.
    pub fn validate(self) -> AppResult<ValidatedBookCreate> {
        let title = require_field(self.title, "title")?;
        let author = require_field(self.author, "author")?;
        let title = trim_to(title, MAX_TITLE_LEN, "title")?;
        let author = trim_to(author, MAX_AUTHOR_LEN, "author")?;
        let year = validate_year(self.year)?;
        let isbn = self
            .isbn
            .map(|raw| trim_optional(raw, MAX_ISBN_LEN, "isbn"))
            .transpose()?
            .flatten();
        Ok(ValidatedBookCreate {
            title,
            author,
            year,
            isbn,
        })
    }
}

impl BookUpdate {
    /// Validate the incoming payload and return a trimmed [`ValidatedBookUpdate`]
    /// ready for persistence.
    pub fn validate(self) -> AppResult<ValidatedBookUpdate> {
        let title = require_field(self.title, "title")?;
        let author = require_field(self.author, "author")?;
        let title = trim_to(title, MAX_TITLE_LEN, "title")?;
        let author = trim_to(author, MAX_AUTHOR_LEN, "author")?;
        let year = validate_year(self.year)?;
        let isbn = self
            .isbn
            .map(|raw| trim_optional(raw, MAX_ISBN_LEN, "isbn"))
            .transpose()?
            .flatten();
        Ok(ValidatedBookUpdate {
            title,
            author,
            year,
            isbn,
        })
    }
}

/// Sanitized form of [`BookCreate`] after trimming and bounds checking.
#[derive(Debug, Clone)]
pub struct ValidatedBookCreate {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Sanitized form of [`BookUpdate`] after trimming and bounds checking.
#[derive(Debug, Clone)]
pub struct ValidatedBookUpdate {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

fn require_field(value: Option<String>, name: &'static str) -> AppResult<String> {
    match value {
        Some(raw) if raw.trim().is_empty() => Err(AppError::Validation(format!(
            "'{name}' must not be empty"
        ))),
        Some(raw) => Ok(raw),
        None => Err(AppError::Validation(format!("'{name}' is required"))),
    }
}

fn trim_to(value: String, max: usize, name: &'static str) -> AppResult<String> {
    let trimmed = value.trim().to_string();
    if trimmed.is_empty() {
        return Err(AppError::Validation(format!("'{name}' must not be empty")));
    }
    if trimmed.chars().count() > max {
        return Err(AppError::Validation(format!(
            "'{name}' must be at most {max} characters"
        )));
    }
    Ok(trimmed)
}

fn trim_optional(value: String, max: usize, name: &'static str) -> AppResult<Option<String>> {
    let trimmed = value.trim().to_string();
    if trimmed.is_empty() {
        return Ok(None);
    }
    if trimmed.chars().count() > max {
        return Err(AppError::Validation(format!(
            "'{name}' must be at most {max} characters"
        )));
    }
    Ok(Some(trimmed))
}

fn validate_year(year: Option<i32>) -> AppResult<Option<i32>> {
    match year {
        None => Ok(None),
        Some(y) if (1..=9999).contains(&y) => Ok(Some(y)),
        Some(y) => Err(AppError::Validation(format!(
            "year must be between 1 and 9999, got {y}"
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_requires_title() {
        let payload = BookCreate {
            title: None,
            author: Some("Ursula K. Le Guin".into()),
            year: Some(1969),
            isbn: None,
        };
        let err = payload.validate().unwrap_err();
        assert!(matches!(err, AppError::Validation(_)));
    }

    #[test]
    fn create_requires_author() {
        let payload = BookCreate {
            title: Some("The Left Hand of Darkness".into()),
            author: None,
            year: None,
            isbn: None,
        };
        let err = payload.validate().unwrap_err();
        assert!(matches!(err, AppError::Validation(_)));
    }

    #[test]
    fn create_rejects_blank_strings() {
        let payload = BookCreate {
            title: Some("   ".into()),
            author: Some("Anon".into()),
            year: None,
            isbn: None,
        };
        let err = payload.validate().unwrap_err();
        assert!(matches!(err, AppError::Validation(_)));
    }

    #[test]
    fn create_trims_and_keeps_optionals() {
        let payload = BookCreate {
            title: Some("  Dune  ".into()),
            author: Some(" Frank Herbert ".into()),
            year: Some(1965),
            isbn: Some(" 978-0-441-17271-9 ".into()),
        };
        let v = payload.validate().unwrap();
        assert_eq!(v.title, "Dune");
        assert_eq!(v.author, "Frank Herbert");
        assert_eq!(v.year, Some(1965));
        assert_eq!(v.isbn.as_deref(), Some("978-0-441-17271-9"));
    }

    #[test]
    fn create_rejects_out_of_range_year() {
        let payload = BookCreate {
            title: Some("Future".into()),
            author: Some("Anon".into()),
            year: Some(0),
            isbn: None,
        };
        let err = payload.validate().unwrap_err();
        assert!(matches!(err, AppError::Validation(_)));
    }

    #[test]
    fn update_requires_title_and_author() {
        let payload = BookUpdate {
            title: None,
            author: Some("X".into()),
            year: None,
            isbn: None,
        };
        assert!(payload.validate().is_err());
    }
}
