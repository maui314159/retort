//! Domain types for the book collection API.

use serde::{Deserialize, Serialize};

/// A book as stored in the database and returned by the API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Payload accepted by `POST /books` and `PUT /books/{id}`.
///
/// `title` and `author` are modeled as `Option` so that *missing* fields are
/// rejected by our own validation (400 with a JSON error body) instead of
/// failing earlier inside the JSON extractor.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Enforce the API contract: title and author are required and must not
    /// be blank. Returns a human-readable message on the first violation.
    pub fn validate(&self) -> Result<(), String> {
        match &self.title {
            None => return Err("title is required".to_string()),
            Some(t) if t.trim().is_empty() => return Err("title must not be empty".to_string()),
            _ => {}
        }
        match &self.author {
            None => return Err("author is required".to_string()),
            Some(a) if a.trim().is_empty() => return Err("author must not be empty".to_string()),
            _ => {}
        }
        Ok(())
    }
}
