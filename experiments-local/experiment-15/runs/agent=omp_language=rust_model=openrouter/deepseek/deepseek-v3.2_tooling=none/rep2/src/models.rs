use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct Book {
    pub id: Uuid,
    #[validate(length(min = 1, message = "Title is required"))]
    pub title: String,
    #[validate(length(min = 1, message = "Author is required"))]
    pub author: String,
    pub year: i64,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateBookRequest {
    #[validate(length(min = 1, message = "Title is required"))]
    pub title: String,
    #[validate(length(min = 1, message = "Author is required"))]
    pub author: String,
    pub year: i64,
    pub isbn: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct UpdateBookRequest {
    #[validate(length(min = 1, message = "Title must not be empty if provided"))]
    pub title: Option<String>,
    #[validate(length(min = 1, message = "Author must not be empty if provided"))]
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl Book {
    pub fn new(title: String, author: String, year: i64, isbn: String) -> Self {
        Self {
            id: Uuid::new_v4(),
            title,
            author,
            year,
            isbn,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use validator::Validate;

    #[test]
    fn test_book_creation() {
        let book = Book::new(
            "Test Title".to_string(),
            "Test Author".to_string(),
            2023,
            "1234567890".to_string(),
        );

        assert_eq!(book.title, "Test Title");
        assert_eq!(book.author, "Test Author");
        assert_eq!(book.year, 2023);
        assert_eq!(book.isbn, "1234567890");
    }

    #[test]
    fn test_create_book_request_validation_valid() {
        let request = CreateBookRequest {
            title: "Valid Title".to_string(),
            author: "Valid Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        assert!(request.validate().is_ok());
    }

    #[test]
    fn test_create_book_request_validation_empty_title() {
        let request = CreateBookRequest {
            title: "".to_string(),
            author: "Valid Author".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        assert!(request.validate().is_err());
    }

    #[test]
    fn test_create_book_request_validation_empty_author() {
        let request = CreateBookRequest {
            title: "Valid Title".to_string(),
            author: "".to_string(),
            year: 2023,
            isbn: "1234567890".to_string(),
        };

        assert!(request.validate().is_err());
    }

    #[test]
    fn test_update_book_request_validation_valid_partial() {
        let request = UpdateBookRequest {
            title: Some("Updated Title".to_string()),
            author: None,
            year: None,
            isbn: None,
        };

        assert!(request.validate().is_ok());
    }

    #[test]
    fn test_update_book_request_validation_empty_title() {
        let request = UpdateBookRequest {
            title: Some("".to_string()),
            author: None,
            year: None,
            isbn: None,
        };

        assert!(request.validate().is_err());
    }
}