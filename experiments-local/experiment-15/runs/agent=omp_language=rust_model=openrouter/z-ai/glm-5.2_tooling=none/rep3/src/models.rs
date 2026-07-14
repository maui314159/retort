use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub isbn: Option<String>,
}

/// Payload for creating a book. `title` and `author` are required.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BookUpdate {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Validation error for a book input.
#[derive(Debug, PartialEq)]
pub struct ValidationError {
    pub field: &'static str,
    pub message: &'static str,
}

/// Validate that title and author are present (non-empty after trimming).
pub fn validate_required(title: &str, author: &str) -> Result<(), ValidationError> {
    if title.trim().is_empty() {
        return Err(ValidationError {
            field: "title",
            message: "title is required and must not be empty",
        });
    }
    if author.trim().is_empty() {
        return Err(ValidationError {
            field: "author",
            message: "author is required and must not be empty",
        });
    }
    Ok(())
}
