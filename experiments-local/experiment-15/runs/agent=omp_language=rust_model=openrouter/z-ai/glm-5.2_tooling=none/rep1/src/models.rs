use chrono::NaiveDateTime;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: NaiveDateTime,
    pub updated_at: NaiveDateTime,
}

/// Payload accepted on POST /books and PUT /books/{id}.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate the payload. `title` and `author` are required and must be
    /// non-empty after trimming. Returns the trimmed values so they are
    /// persisted consistently.
    pub fn validate(&self) -> Result<BookInput, String> {
        let title = self.title.trim().to_string();
        let author = self.author.trim().to_string();
        if title.is_empty() {
            return Err("title is required".to_string());
        }
        if author.is_empty() {
            return Err("author is required".to_string());
        }
        if let Some(y) = self.year {
            if y < 0 {
                return Err("year must be non-negative".to_string());
            }
        }
        Ok(BookInput {
            title,
            author,
            year: self.year,
            isbn: self.isbn.as_ref().map(|s| s.trim().to_string()),
        })
    }
}
