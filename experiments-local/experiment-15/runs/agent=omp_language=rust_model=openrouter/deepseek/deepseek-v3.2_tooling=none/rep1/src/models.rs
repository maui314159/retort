use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<chrono::DateTime<chrono::Utc>>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBook {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl Book {
    pub fn new(create_book: CreateBook) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            title: create_book.title,
            author: create_book.author,
            year: create_book.year,
            isbn: create_book.isbn,
            created_at: None,
            updated_at: None,
        }
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.title.trim().is_empty() {
            return Err("Title is required".to_string());
        }
        if self.author.trim().is_empty() {
            return Err("Author is required".to_string());
        }
        if self.year < 1000 || self.year > 9999 {
            return Err("Year must be between 1000 and 9999".to_string());
        }
        if self.isbn.trim().is_empty() {
            return Err("ISBN is required".to_string());
        }
        Ok(())
    }
}

impl CreateBook {
    pub fn validate(&self) -> Result<(), String> {
        if self.title.trim().is_empty() {
            return Err("Title is required".to_string());
        }
        if self.author.trim().is_empty() {
            return Err("Author is required".to_string());
        }
        if self.year < 1000 || self.year > 9999 {
            return Err("Year must be between 1000 and 9999".to_string());
        }
        if self.isbn.trim().is_empty() {
            return Err("ISBN is required".to_string());
        }
        Ok(())
    }
}