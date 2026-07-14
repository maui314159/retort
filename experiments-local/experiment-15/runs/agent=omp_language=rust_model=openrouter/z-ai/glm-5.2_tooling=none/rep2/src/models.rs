use serde::{Deserialize, Serialize};

/// A book stored in the collection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Payload for creating a book. `title` and `author` are required; `year` and
/// `isbn` are optional.
#[derive(Debug, Clone, Deserialize)]
pub struct CreateBook {
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Payload for updating a book. All fields are optional — only provided fields
/// are overwritten.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl CreateBook {
    /// Validate the payload. `title` and `author` must be non-empty after
    /// trimming; `year` must be plausible if present.
    pub fn validate(&self) -> Result<(), String> {
        if self.title.trim().is_empty() {
            return Err("title is required".to_string());
        }
        if self.author.trim().is_empty() {
            return Err("author is required".to_string());
        }
        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                return Err("year must be between 0 and 9999".to_string());
            }
        }
        if let Some(isbn) = &self.isbn {
            if isbn.trim().is_empty() {
                return Err("isbn must not be blank if provided".to_string());
            }
        }
        Ok(())
    }
}

impl UpdateBook {
    /// Validate the partial update. At least one field must be present and each
    /// present field must be valid on its own.
    pub fn validate(&self) -> Result<(), String> {
        let any_present = self.title.is_some()
            || self.author.is_some()
            || self.year.is_some()
            || self.isbn.is_some();
        if !any_present {
            return Err("at least one field must be provided to update".to_string());
        }
        if let Some(title) = &self.title {
            if title.trim().is_empty() {
                return Err("title must not be empty".to_string());
            }
        }
        if let Some(author) = &self.author {
            if author.trim().is_empty() {
                return Err("author must not be empty".to_string());
            }
        }
        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                return Err("year must be between 0 and 9999".to_string());
            }
        }
        if let Some(isbn) = &self.isbn {
            if isbn.trim().is_empty() {
                return Err("isbn must not be blank if provided".to_string());
            }
        }
        Ok(())
    }
}
