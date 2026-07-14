use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
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
            return Err("title is required".to_string());
        }
        if self.author.trim().is_empty() {
            return Err("author is required".to_string());
        }
        Ok(())
    }
}

impl UpdateBook {
    pub fn apply_to(&self, existing: &Book) -> Book {
        Book {
            id: existing.id,
            title: self.title.clone().unwrap_or_else(|| existing.title.clone()),
            author: self.author.clone().unwrap_or_else(|| existing.author.clone()),
            year: self.year.or(existing.year),
            isbn: self.isbn.clone().or_else(|| existing.isbn.clone()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_rejects_empty_title_and_author() {
        let input = CreateBook {
            title: "  ".to_string(),
            author: "x".to_string(),
            year: None,
            isbn: None,
        };
        let err = input.validate().unwrap_err();
        assert_eq!(err, "title is required");

        let input = CreateBook {
            title: "t".to_string(),
            author: "".to_string(),
            year: None,
            isbn: None,
        };
        let err = input.validate().unwrap_err();
        assert_eq!(err, "author is required");
    }

    #[test]
    fn validate_accepts_non_empty_fields() {
        let input = CreateBook {
            title: "Title".to_string(),
            author: "Author".to_string(),
            year: Some(2020),
            isbn: Some("isbn".to_string()),
        };
        assert!(input.validate().is_ok());
    }

    #[test]
    fn update_apply_preserves_untouched_fields() {
        let existing = Book {
            id: 1,
            title: "Old".to_string(),
            author: "A".to_string(),
            year: Some(2000),
            isbn: Some("i".to_string()),
        };
        let update = UpdateBook {
            title: Some("New".to_string()),
            author: None,
            year: Some(2021),
            isbn: None,
        };
        let result = update.apply_to(&existing);
        assert_eq!(result.id, 1);
        assert_eq!(result.title, "New");
        assert_eq!(result.author, "A");
        assert_eq!(result.year, Some(2021));
        assert_eq!(result.isbn, Some("i".to_string()));
    }
}
