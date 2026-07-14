use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
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
            return Err("title is required".into());
        }
        if self.author.trim().is_empty() {
            return Err("author is required".into());
        }
        Ok(())
    }
}

impl UpdateBook {
    pub fn validate(&self) -> Result<(), String> {
        if let Some(ref t) = self.title {
            if t.trim().is_empty() {
                return Err("title must not be empty".into());
            }
        }
        if let Some(ref a) = self.author {
            if a.trim().is_empty() {
                return Err("author must not be empty".into());
            }
        }
        Ok(())
    }
}

impl CreateBook {
    pub fn into_book(self) -> Book {
        Book {
            id: Uuid::new_v4().to_string(),
            title: self.title,
            author: self.author,
            year: self.year,
            isbn: self.isbn,
        }
    }
}
