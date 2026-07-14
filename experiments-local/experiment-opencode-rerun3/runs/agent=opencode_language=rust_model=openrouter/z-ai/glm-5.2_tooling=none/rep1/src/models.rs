use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Returns the trimmed, non-empty title and author if validation passes.
    pub fn validated(self) -> Result<(String, String, Option<i32>, Option<String>), &'static str> {
        let title = self
            .title
            .map(|t| t.trim().to_string())
            .filter(|t| !t.is_empty())
            .ok_or("title is required and must not be empty")?;
        let author = self
            .author
            .map(|a| a.trim().to_string())
            .filter(|a| !a.is_empty())
            .ok_or("author is required and must not be empty")?;
        Ok((title, author, self.year, self.isbn.map(|s| s.trim().to_string())))
    }
}
