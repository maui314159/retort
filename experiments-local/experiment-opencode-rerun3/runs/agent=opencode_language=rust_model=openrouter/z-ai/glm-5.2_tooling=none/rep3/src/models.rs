use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl CreateBook {
    pub fn validate(&self) -> Result<(), String> {
        if self.title.trim().is_empty() {
            return Err("title is required".to_string());
        }
        if self.author.trim().is_empty() {
            return Err("author is required".to_string());
        }
        if let Some(y) = self.year {
            if !(0..=9999).contains(&y) {
                return Err("year must be between 0 and 9999".to_string());
            }
        }
        Ok(())
    }
}

impl UpdateBook {
    pub fn validate(&self) -> Result<(), String> {
        if let Some(t) = &self.title {
            if t.trim().is_empty() {
                return Err("title must not be empty".to_string());
            }
        }
        if let Some(a) = &self.author {
            if a.trim().is_empty() {
                return Err("author must not be empty".to_string());
            }
        }
        if let Some(y) = self.year {
            if !(0..=9999).contains(&y) {
                return Err("year must be between 0 and 9999".to_string());
            }
        }
        Ok(())
    }
}
