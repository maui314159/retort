use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CreateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl CreateBook {
    pub fn validate(&self) -> Result<(String, String), String> {
        let title = self
            .title
            .as_ref()
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .ok_or_else(|| "title is required".to_string())?
            .to_string();
        let author = self
            .author
            .as_ref()
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .ok_or_else(|| "author is required".to_string())?
            .to_string();
        Ok((title, author))
    }
}

impl UpdateBook {
    pub fn into_validated(self) -> Result<Self, String> {
        if let Some(t) = &self.title {
            if t.trim().is_empty() {
                return Err("title must not be empty".into());
            }
        }
        if let Some(a) = &self.author {
            if a.trim().is_empty() {
                return Err("author must not be empty".into());
            }
        }
        Ok(self)
    }
}
