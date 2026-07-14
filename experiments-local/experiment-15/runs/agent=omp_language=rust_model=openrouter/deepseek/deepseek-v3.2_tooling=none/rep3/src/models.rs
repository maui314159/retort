use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBookRequest {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl CreateBookRequest {
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.title.trim().is_empty() {
            return Err(ValidationError("Title is required".into()));
        }
        if self.author.trim().is_empty() {
            return Err(ValidationError("Author is required".into()));
        }
        if let Some(year) = self.year {
            if year < 0 || year > 3000 {
                return Err(ValidationError("Year must be between 0 and 3000".into()));
            }
        }
        Ok(())
    }
}

impl UpdateBookRequest {
    pub fn validate(&self) -> Result<(), ValidationError> {
        if let Some(title) = &self.title {
            if title.trim().is_empty() {
                return Err(ValidationError("Title cannot be empty".into()));
            }
        }
        if let Some(author) = &self.author {
            if author.trim().is_empty() {
                return Err(ValidationError("Author cannot be empty".into()));
            }
        }
        if let Some(year) = self.year {
            if year < 0 || year > 3000 {
                return Err(ValidationError("Year must be between 0 and 3000".into()));
            }
        }
        Ok(())
    }
}
#[derive(Debug, thiserror::Error)]
#[error("{0}")]
pub struct ValidationError(String);

impl ValidationError {
    pub fn message(&self) -> &str {
        &self.0
    }
}
impl Book {
    pub fn new(create_req: CreateBookRequest) -> Self {
        let id = Uuid::new_v4().to_string();
        Self {
            id,
            title: create_req.title,
            author: create_req.author,
            year: create_req.year,
            isbn: create_req.isbn,
            created_at: None,
            updated_at: None,
        }
    }
    pub fn update(&mut self, update_req: UpdateBookRequest) {
        if let Some(title) = update_req.title {
            self.title = title;
        }
        if let Some(author) = update_req.author {
            self.author = author;
        }
        if let Some(year) = update_req.year {
            self.year = Some(year);
        }
        if let Some(isbn) = update_req.isbn {
            self.isbn = Some(isbn);
        }
    }
}